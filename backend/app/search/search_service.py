"""SearchService — indexation et recherche."""

from __future__ import annotations

import logging
import math
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.search.search_exceptions import (
    SearchDisabledError,
    SearchNotFoundError,
    SearchValidationError,
)
from app.search.search_highlighting import build_snippet
from app.search.search_logging import query_hash, safe_search_log_context, sanitize_search_error
from app.search.search_models import ElfisSearchDocument
from app.search.search_registry import SearchIndexerRegistry, bootstrap_indexers, default_indexer_registry
from app.search.search_repository import SearchRepository
from app.search.search_schemas import (
    BuiltSearchDocument,
    SearchIndexRequest,
    SearchIndexResult,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
    SuggestionItem,
)
from app.search.search_security import (
    assert_page_size,
    assert_query,
    assert_resource_type,
    assert_sort,
    filter_metadata,
)
from app.search.search_types import IndexStatus

logger = logging.getLogger(__name__)


def _as_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class SearchService:
    def __init__(
        self,
        db: Session,
        *,
        registry: SearchIndexerRegistry | None = None,
    ):
        self._db = db
        self._repo = SearchRepository(db)
        self._registry = registry or bootstrap_indexers(default_indexer_registry)

    def index_resource(self, request: SearchIndexRequest) -> SearchIndexResult:
        if not settings.elfis_search_enabled:
            raise SearchDisabledError()

        rtype = assert_resource_type(request.resource_type)
        if not request.organization_id:
            raise SearchValidationError("organization_id requis")
        if not (request.resource_id or "").strip():
            raise SearchValidationError("resource_id requis")

        indexer = self._registry.get(rtype)
        resource = indexer.load_resource(
            self._db,
            organization_id=request.organization_id,
            resource_id=request.resource_id,
        )
        built = indexer.build_search_document(
            resource,
            organization_id=request.organization_id,
            resource_version=request.resource_version,
            db=self._db,
        )
        if not (built.search_text or "").strip() and not (built.title or "").strip():
            raise SearchValidationError("Document d'index vide")

        return self._persist_built(built, request)

    def _persist_built(
        self, built: BuiltSearchDocument, request: SearchIndexRequest
    ) -> SearchIndexResult:
        version = int(built.resource_version or request.resource_version or 1)
        idem = f"search:{built.organization_id}:{built.resource_type}:{built.resource_id}:{version}"
        existing = self._repo.find_resource(
            organization_id=built.organization_id,
            resource_type=built.resource_type,
            resource_id=built.resource_id,
            resource_version=version,
        )
        now = datetime.utcnow()
        if (
            existing
            and not request.force_reindex
            and existing.content_hash
            and existing.content_hash == built.content_hash
            and existing.is_active
        ):
            return SearchIndexResult(
                search_document_id=existing.search_document_id,
                resource_type=built.resource_type,
                resource_id=built.resource_id,
                status=IndexStatus.UNCHANGED,
                indexed=True,
                created=False,
            )

        created = existing is None
        row = existing or ElfisSearchDocument(
            id=str(uuid.uuid4()),
            search_document_id=str(uuid.uuid4()),
            organization_id=built.organization_id,
            created_at=now,
        )
        row.user_id = request.user_id or built.user_id
        row.resource_type = built.resource_type
        row.resource_id = built.resource_id
        row.resource_version = version
        row.title = built.title
        row.subtitle = built.subtitle
        row.content = built.content
        row.search_text = built.search_text
        row.status = built.status
        row.category = built.category
        row.document_date = built.document_date
        row.amount = built.amount
        row.currency = built.currency
        row.action_url = built.action_url
        row.metadata_json = filter_metadata(built.metadata)
        row.is_active = True
        row.deleted_at = None
        row.indexed_at = now
        row.updated_at = now
        row.source_event_id = request.source_event_id
        row.correlation_id = request.correlation_id
        row.content_hash = built.content_hash
        row.idempotency_key = idem
        self._repo.save(row)

        event_name = (
            EventNames.SEARCH_DOCUMENT_INDEXED if created else EventNames.SEARCH_DOCUMENT_UPDATED
        )
        self._publish(event_name, row)
        logger.info(
            "search_document_indexed",
            extra=safe_search_log_context(
                organization_id=row.organization_id,
                search_document_id=row.search_document_id,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                status=IndexStatus.INDEXED if created else IndexStatus.UPDATED,
                correlation_id=row.correlation_id,
            ),
        )
        return SearchIndexResult(
            search_document_id=row.search_document_id,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            status=IndexStatus.INDEXED if created else IndexStatus.UPDATED,
            indexed=True,
            created=created,
        )

    def remove_resource(
        self,
        *,
        organization_id: int,
        resource_type: str,
        resource_id: str,
        resource_version: int = 1,
    ) -> SearchIndexResult:
        if not settings.elfis_search_enabled:
            raise SearchDisabledError()
        rtype = assert_resource_type(resource_type)
        row = self._repo.find_resource(
            organization_id=organization_id,
            resource_type=rtype,
            resource_id=resource_id,
            resource_version=resource_version,
        )
        if not row:
            raise SearchNotFoundError()
        self._repo.soft_delete(row)
        self._publish(EventNames.SEARCH_DOCUMENT_REMOVED, row)
        return SearchIndexResult(
            search_document_id=row.search_document_id,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            status=IndexStatus.REMOVED,
            indexed=False,
            created=False,
        )

    def restore_resource(self, search_document_id: str) -> SearchIndexResult:
        row = self._repo.find_by_search_id(search_document_id)
        if not row:
            raise SearchNotFoundError()
        self._repo.restore(row)
        self._publish(EventNames.SEARCH_DOCUMENT_INDEXED, row)
        return SearchIndexResult(
            search_document_id=row.search_document_id,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            status=IndexStatus.INDEXED,
            indexed=True,
            created=False,
        )

    def get_search_document(
        self, *, search_document_id: str, organization_id: int | None = None
    ) -> ElfisSearchDocument:
        row = self._repo.find_by_search_id(search_document_id)
        if not row:
            raise SearchNotFoundError()
        if organization_id is not None and row.organization_id != organization_id:
            raise SearchNotFoundError()
        return row

    def search(self, *, organization_id: int, query: SearchQuery) -> SearchResponse:
        if not settings.elfis_search_enabled:
            raise SearchDisabledError()
        started = time.monotonic()
        q = assert_query(query.query)
        page_size = assert_page_size(query.page_size)
        page = max(1, int(query.page or 1))
        sort = assert_sort(query.sort, has_query=bool(q))

        if query.resource_types:
            for rt in query.resource_types:
                assert_resource_type(rt)

        rows, total = self._repo.search(
            organization_id=organization_id,
            query=q,
            resource_types=query.resource_types,
            statuses=query.statuses,
            categories=query.categories,
            date_from=query.date_from,
            date_to=query.date_to,
            amount_min=query.amount_min,
            amount_max=query.amount_max,
            currency=query.currency,
            requires_review=query.requires_review,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        items = [
            SearchResultItem(
                search_document_id=doc.search_document_id,
                resource_type=doc.resource_type,
                resource_id=doc.resource_id,
                title=doc.title,
                subtitle=doc.subtitle,
                snippet=build_snippet(doc.content or doc.search_text, q),
                status=doc.status,
                category=doc.category,
                document_date=doc.document_date,
                amount=float(doc.amount) if doc.amount is not None else None,
                currency=doc.currency,
                action_url=doc.action_url,
                score=score,
                metadata=filter_metadata(doc.metadata_json if isinstance(doc.metadata_json, dict) else {}),
            )
            for doc, score in rows
        ]
        duration = int((time.monotonic() - started) * 1000)
        logger.info(
            "search_executed",
            extra=safe_search_log_context(
                organization_id=organization_id,
                query_hash_value=query_hash(q),
                resource_types=query.resource_types,
                result_count=len(items),
                execution_time_ms=duration,
            ),
        )
        total_pages = math.ceil(total / page_size) if page_size else 0
        return SearchResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            query=q,
            filters_applied={
                "resource_types": query.resource_types,
                "statuses": query.statuses,
                "categories": query.categories,
                "sort": sort,
                "requires_review": query.requires_review,
            },
            execution_time_ms=duration,
        )

    def suggest(
        self, *, organization_id: int, query: str, limit: int | None = None
    ) -> list[SuggestionItem]:
        q = assert_query(query)
        if not q or len(q) < 2:
            return []
        lim = limit or int(settings.elfis_search_suggestion_limit)
        lim = max(1, min(lim, 20))
        rows = self._repo.suggest(organization_id=organization_id, query=q, limit=lim)
        return [
            SuggestionItem(
                title=r.title,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                action_url=r.action_url,
            )
            for r in rows
        ]

    def reindex_resource(self, request: SearchIndexRequest) -> SearchIndexResult:
        request.force_reindex = True
        return self.index_resource(request)

    def _publish(self, event_name: str, row: ElfisSearchDocument) -> None:
        safe_publish(
            self._db,
            DomainEvent(
                event_name=event_name,
                organization_id=row.organization_id,
                aggregate_type="search_document",
                aggregate_id=row.search_document_id,
                payload={
                    "search_document_id": row.search_document_id,
                    "organization_id": row.organization_id,
                    "resource_type": row.resource_type,
                    "resource_id": row.resource_id,
                    "status": "active" if row.is_active else "removed",
                    "correlation_id": row.correlation_id,
                },
                metadata={"source": "search_engine"},
                correlation_id=_as_uuid(row.correlation_id) or uuid.uuid4(),
            ),
        )

    def publish_index_failed(
        self,
        *,
        organization_id: int,
        resource_type: str,
        resource_id: str,
        correlation_id: str | None = None,
        error: str | None = None,
    ) -> None:
        safe_publish(
            self._db,
            DomainEvent(
                event_name=EventNames.SEARCH_INDEX_FAILED,
                organization_id=organization_id,
                aggregate_type="search_document",
                aggregate_id=resource_id,
                payload={
                    "organization_id": organization_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "status": IndexStatus.FAILED,
                    "correlation_id": correlation_id,
                    "error": sanitize_search_error(error),
                },
                metadata={"source": "search_engine"},
                correlation_id=_as_uuid(correlation_id) or uuid.uuid4(),
            ),
        )
