"""Persistance et requêtes Search."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.search.search_models import ElfisSearchDocument
from app.search.search_types import SearchSort


class SearchRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_by_search_id(self, search_document_id: str) -> ElfisSearchDocument | None:
        return (
            self._db.query(ElfisSearchDocument)
            .filter(ElfisSearchDocument.search_document_id == search_document_id)
            .first()
        )

    def find_resource(
        self,
        *,
        organization_id: int,
        resource_type: str,
        resource_id: str,
        resource_version: int = 1,
    ) -> ElfisSearchDocument | None:
        return (
            self._db.query(ElfisSearchDocument)
            .filter(
                ElfisSearchDocument.organization_id == organization_id,
                ElfisSearchDocument.resource_type == resource_type,
                ElfisSearchDocument.resource_id == resource_id,
                ElfisSearchDocument.resource_version == resource_version,
            )
            .first()
        )

    def save(self, row: ElfisSearchDocument, *, commit: bool = True) -> ElfisSearchDocument:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def soft_delete(self, row: ElfisSearchDocument) -> ElfisSearchDocument:
        row.is_active = False
        row.deleted_at = datetime.utcnow()
        return self.save(row)

    def restore(self, row: ElfisSearchDocument) -> ElfisSearchDocument:
        row.is_active = True
        row.deleted_at = None
        row.indexed_at = datetime.utcnow()
        return self.save(row)

    def _is_postgres(self) -> bool:
        bind = self._db.get_bind()
        return bool(bind and bind.dialect.name == "postgresql")

    def search(
        self,
        *,
        organization_id: int,
        query: str | None,
        resource_types: list[str] | None = None,
        statuses: list[str] | None = None,
        categories: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        currency: str | None = None,
        requires_review: bool | None = None,
        sort: str = SearchSort.NEWEST,
        page: int = 1,
        page_size: int = 20,
        active_only: bool = True,
    ) -> tuple[list[tuple[ElfisSearchDocument, float]], int]:
        q = self._db.query(ElfisSearchDocument).filter(
            ElfisSearchDocument.organization_id == organization_id
        )
        if active_only:
            q = q.filter(ElfisSearchDocument.is_active.is_(True))
        if resource_types:
            q = q.filter(ElfisSearchDocument.resource_type.in_(resource_types))
        if statuses:
            q = q.filter(ElfisSearchDocument.status.in_(statuses))
        if categories:
            q = q.filter(ElfisSearchDocument.category.in_(categories))
        if date_from is not None:
            q = q.filter(ElfisSearchDocument.document_date >= date_from)
        if date_to is not None:
            q = q.filter(ElfisSearchDocument.document_date <= date_to)
        if amount_min is not None:
            q = q.filter(ElfisSearchDocument.amount >= amount_min)
        if amount_max is not None:
            q = q.filter(ElfisSearchDocument.amount <= amount_max)
        if currency:
            q = q.filter(ElfisSearchDocument.currency == currency)
        if requires_review is not None:
            # metadata JSON — SQLite/Postgres via cast string fallback
            # Filtre applicatif après lecture pour compat SQLite
            pass

        score_expr = None
        if query:
            if self._is_postgres():
                lang = (settings.elfis_search_language or "simple").strip() or "simple"
                ts_query = func.plainto_tsquery(lang, query)
                score_expr = func.coalesce(
                    func.ts_rank_cd(ElfisSearchDocument.search_vector, ts_query),
                    0,
                )
                q = q.filter(ElfisSearchDocument.search_vector.op("@@")(ts_query))
            else:
                like = f"%{query}%"
                q = q.filter(
                    or_(
                        ElfisSearchDocument.title.ilike(like),
                        ElfisSearchDocument.subtitle.ilike(like),
                        ElfisSearchDocument.search_text.ilike(like),
                    )
                )

        total = q.count()

        if sort == SearchSort.OLDEST:
            q = q.order_by(
                asc(ElfisSearchDocument.document_date),
                asc(ElfisSearchDocument.indexed_at),
            )
        elif sort == SearchSort.AMOUNT_HIGH:
            q = q.order_by(desc(ElfisSearchDocument.amount))
        elif sort == SearchSort.AMOUNT_LOW:
            q = q.order_by(asc(ElfisSearchDocument.amount))
        elif sort == SearchSort.RELEVANCE and score_expr is not None:
            q = q.order_by(desc(score_expr), desc(ElfisSearchDocument.indexed_at))
        else:
            q = q.order_by(
                desc(ElfisSearchDocument.document_date),
                desc(ElfisSearchDocument.indexed_at),
            )
        page = max(1, page)
        page_size = max(1, page_size)

        if score_expr is not None:
            rows_raw = (
                q.add_columns(score_expr.label("rank"))
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            pairs = [(r[0], float(r[1] or 0.0)) for r in rows_raw]
        else:
            docs = q.offset((page - 1) * page_size).limit(page_size).all()
            pairs = [(doc, self._like_score(doc, query) if query else 0.0) for doc in docs]

        results: list[tuple[ElfisSearchDocument, float]] = []
        for doc, rank in pairs:
            if requires_review is not None:
                meta = doc.metadata_json if isinstance(doc.metadata_json, dict) else {}
                if bool(meta.get("requires_review")) != requires_review:
                    continue
            results.append((doc, rank))

        if requires_review is not None:
            total = len(results) if page == 1 and len(results) < page_size else total

        return results, total

    def _like_score(self, doc: ElfisSearchDocument, query: str | None) -> float:
        if not query:
            return 0.0
        q = query.lower()
        score = 0.0
        if q in (doc.title or "").lower():
            score += 3.0
        if q in (doc.subtitle or "").lower():
            score += 2.0
        if q in (doc.search_text or "").lower():
            score += 1.0
        return score

    def suggest(
        self,
        *,
        organization_id: int,
        query: str,
        limit: int = 10,
    ) -> list[ElfisSearchDocument]:
        like = f"%{query}%"
        return (
            self._db.query(ElfisSearchDocument)
            .filter(
                ElfisSearchDocument.organization_id == organization_id,
                ElfisSearchDocument.is_active.is_(True),
                or_(
                    ElfisSearchDocument.title.ilike(like),
                    ElfisSearchDocument.subtitle.ilike(like),
                ),
            )
            .order_by(desc(ElfisSearchDocument.indexed_at))
            .limit(limit)
            .all()
        )

    def list_platform(
        self,
        *,
        organization_id: int | None = None,
        resource_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisSearchDocument], int]:
        q = self._db.query(ElfisSearchDocument)
        if organization_id is not None:
            q = q.filter(ElfisSearchDocument.organization_id == organization_id)
        if resource_type:
            q = q.filter(ElfisSearchDocument.resource_type == resource_type)
        if is_active is not None:
            q = q.filter(ElfisSearchDocument.is_active.is_(is_active))
        total = q.count()
        rows = (
            q.order_by(desc(ElfisSearchDocument.indexed_at))
            .offset((max(1, page) - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def iter_resource_ids_for_org(
        self,
        *,
        organization_id: int,
        resource_type: str,
        offset: int,
        limit: int,
    ) -> list[str]:
        """Utilisé pour réindexation par lots — IDs déjà indexés ou sources selon type."""
        rows = (
            self._db.query(ElfisSearchDocument.resource_id)
            .filter(
                ElfisSearchDocument.organization_id == organization_id,
                ElfisSearchDocument.resource_type == resource_type,
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [r[0] for r in rows]
