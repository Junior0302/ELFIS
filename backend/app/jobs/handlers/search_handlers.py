"""Handlers Job Queue — Search Engine."""

from __future__ import annotations

from app.config import settings
from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames
from app.models_saas import Contact, Customer
from app.models_vault import VaultDocument
from app.search.search_exceptions import (
    SearchDisabledError,
    SearchNotFoundError,
    SearchValidationError,
)
from app.search.search_registry import bootstrap_indexers
from app.search.search_schemas import SearchIndexRequest
from app.search.search_service import SearchService
from app.search.search_types import INDEXED_RESOURCE_TYPES_V1, SearchResourceTypes
from app.ai.ai_models import ElfisDocumentAnalysis
from app.accounting.accounting_models import ElfisAccountingEntry, ElfisAccountingProposal
from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
import uuid


def _session(context: JobContext):
    if context._db is not None:
        return context._db, False
    if context._session_factory is None:
        raise RetryableJobError("session indisponible")
    return context._session_factory(), True


class SearchIndexResourceJobHandler(JobHandler):
    handler_name = "search_index_resource_v1"
    job_name = JobNames.SEARCH_INDEX_RESOURCE

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        resource_type = str(payload.get("resource_type") or "").strip()
        resource_id = str(payload.get("resource_id") or "").strip()
        if not resource_type or not resource_id:
            raise PermanentJobError("resource_type et resource_id requis")
        version = int(payload.get("resource_version") or 1)
        org_id = int(job.organization_id or payload.get("organization_id") or 0)
        if not org_id:
            raise PermanentJobError("organization_id requis")

        context.update_progress(20, "indexing")
        bootstrap_indexers()
        db, own = _session(context)
        try:
            result = SearchService(db).index_resource(
                SearchIndexRequest(
                    organization_id=org_id,
                    user_id=job.user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_version=version,
                    source_event_id=str(payload.get("source_event_id") or "") or None,
                    correlation_id=job.correlation_id,
                    force_reindex=bool(payload.get("force_reindex")),
                )
            )
            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message=result.status,
                result={
                    "resource_type": result.resource_type,
                    "resource_id": result.resource_id,
                    "indexed": result.indexed,
                    "search_document_id": result.search_document_id,
                },
            )
        except SearchDisabledError as exc:
            raise PermanentJobError(exc.message) from None
        except SearchNotFoundError as exc:
            raise PermanentJobError(exc.message) from None
        except SearchValidationError as exc:
            SearchService(db).publish_index_failed(
                organization_id=org_id,
                resource_type=resource_type,
                resource_id=resource_id,
                correlation_id=job.correlation_id,
                error=exc.message,
            )
            raise PermanentJobError(exc.message) from None
        finally:
            if own:
                db.close()


class SearchRemoveResourceJobHandler(JobHandler):
    handler_name = "search_remove_resource_v1"
    job_name = JobNames.SEARCH_REMOVE_RESOURCE

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        resource_type = str(payload.get("resource_type") or "").strip()
        resource_id = str(payload.get("resource_id") or "").strip()
        org_id = int(job.organization_id or 0)
        version = int(payload.get("resource_version") or 1)
        if not resource_type or not resource_id or not org_id:
            raise PermanentJobError("payload incomplet")
        db, own = _session(context)
        try:
            result = SearchService(db).remove_resource(
                organization_id=org_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_version=version,
            )
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="removed",
                result={
                    "resource_type": result.resource_type,
                    "resource_id": result.resource_id,
                    "indexed": False,
                    "search_document_id": result.search_document_id,
                },
            )
        except SearchNotFoundError:
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="already_absent",
                result={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "indexed": False,
                    "search_document_id": None,
                },
            )
        finally:
            if own:
                db.close()


class SearchReindexOrganizationJobHandler(JobHandler):
    handler_name = "search_reindex_organization_v1"
    job_name = JobNames.SEARCH_REINDEX_ORGANIZATION

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        if not settings.elfis_search_enabled:
            raise PermanentJobError("Search Engine désactivé")
        org_id = int(job.organization_id or (job.payload or {}).get("organization_id") or 0)
        if not org_id:
            raise PermanentJobError("organization_id requis")
        batch = max(1, int(settings.elfis_search_reindex_batch_size))
        bootstrap_indexers()
        db, own = _session(context)
        try:
            safe_publish(
                db,
                DomainEvent(
                    event_name=EventNames.SEARCH_ORGANIZATION_REINDEX_STARTED,
                    organization_id=org_id,
                    aggregate_type="organization",
                    aggregate_id=str(org_id),
                    payload={"organization_id": org_id, "job_id": job.job_id},
                    metadata={"source": "search_reindex"},
                    correlation_id=uuid.uuid4(),
                ),
            )
            svc = SearchService(db)
            total_indexed = 0
            sources = list(_iter_org_resources(db, org_id))
            total = len(sources)
            for i in range(0, total, batch):
                chunk = sources[i : i + batch]
                for rtype, rid, ver in chunk:
                    try:
                        svc.index_resource(
                            SearchIndexRequest(
                                organization_id=org_id,
                                resource_type=rtype,
                                resource_id=rid,
                                resource_version=ver,
                                force_reindex=True,
                                correlation_id=job.correlation_id,
                            )
                        )
                        total_indexed += 1
                    except Exception:
                        continue
                progress = int(min(99, ((i + len(chunk)) / max(1, total)) * 100))
                context.update_progress(progress, f"batch_{i // batch + 1}")

            safe_publish(
                db,
                DomainEvent(
                    event_name=EventNames.SEARCH_ORGANIZATION_REINDEX_COMPLETED,
                    organization_id=org_id,
                    aggregate_type="organization",
                    aggregate_id=str(org_id),
                    payload={
                        "organization_id": org_id,
                        "job_id": job.job_id,
                        "indexed_count": total_indexed,
                    },
                    metadata={"source": "search_reindex"},
                    correlation_id=uuid.uuid4(),
                ),
            )
            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="reindex_done",
                result={
                    "organization_id": org_id,
                    "indexed_count": total_indexed,
                    "total_candidates": total,
                },
            )
        finally:
            if own:
                db.close()


def _iter_org_resources(db, org_id: int):
    for doc in db.query(VaultDocument).filter(VaultDocument.organization_id == org_id).yield_per(50):
        yield SearchResourceTypes.VAULT_DOCUMENT, doc.id, int(doc.version or 1)
    for row in (
        db.query(ElfisDocumentTextExtraction)
        .filter(ElfisDocumentTextExtraction.organization_id == org_id)
        .yield_per(50)
    ):
        yield (
            SearchResourceTypes.DOCUMENT_TEXT_EXTRACTION,
            row.extraction_id,
            int(row.document_version or 1),
        )
    for row in (
        db.query(ElfisDocumentAnalysis)
        .filter(ElfisDocumentAnalysis.organization_id == org_id)
        .yield_per(50)
    ):
        yield SearchResourceTypes.DOCUMENT_ANALYSIS, row.analysis_id, int(row.document_version or 1)
    for row in (
        db.query(ElfisAccountingProposal)
        .filter(ElfisAccountingProposal.organization_id == org_id)
        .yield_per(50)
    ):
        yield SearchResourceTypes.ACCOUNTING_PROPOSAL, row.proposal_id, int(row.document_version or 1)
    for row in (
        db.query(ElfisAccountingEntry)
        .filter(ElfisAccountingEntry.organization_id == org_id)
        .yield_per(50)
    ):
        yield SearchResourceTypes.ACCOUNTING_ENTRY, row.entry_id, 1
    for c in db.query(Customer).filter(Customer.organization_id == org_id).yield_per(50):
        yield SearchResourceTypes.CUSTOMER, str(c.id), 1
    for c in db.query(Contact).filter(Contact.organization_id == org_id).yield_per(50):
        if c.contact_type in ("customer", "customer_and_supplier", "prospect"):
            yield SearchResourceTypes.CUSTOMER, f"contact:{c.id}", 1
        if c.contact_type in ("supplier", "customer_and_supplier"):
            yield SearchResourceTypes.SUPPLIER, f"contact:{c.id}", 1
