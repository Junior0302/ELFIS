"""Event Bus ↔ Search Engine (enqueue only, best-effort)."""

from __future__ import annotations

import logging

from app.config import settings
from app.events.event_context import EventContext
from app.events.event_registry import EventHandler
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.search.search_types import SearchResourceTypes

logger = logging.getLogger(__name__)


def _enqueue_index(
    event: DomainEvent,
    context: EventContext,
    *,
    resource_type: str,
    resource_id: str,
    resource_version: int = 1,
) -> None:
    if not settings.elfis_auto_search_indexing_enabled:
        return
    if not resource_id:
        return
    org_id = event.organization_id
    idem = f"search:{org_id}:{resource_type}:{resource_id}:{resource_version}"
    try:
        JobService(context.db).enqueue(
            JobRequest(
                job_name=JobNames.SEARCH_INDEX_RESOURCE,
                organization_id=org_id,
                payload={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_version": resource_version,
                    "source_event_id": str(event.event_id),
                },
                idempotency_key=idem,
                correlation_id=str(event.correlation_id) if event.correlation_id else None,
                causation_event_id=str(event.event_id),
            )
        )
    except Exception:
        logger.exception(
            "search_index_enqueue_failed",
            extra={
                "organization_id": org_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "event_id": str(event.event_id),
            },
        )


class VaultArchivedSearchIndexHandler(EventHandler):
    handler_name = "vault_archived_search_index_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.VAULT_DOCUMENT_ARCHIVED:
            return
        payload = event.payload or {}
        vid = str(payload.get("vault_document_id") or "").strip()
        version = int(payload.get("version") or payload.get("document_version") or 1)
        _enqueue_index(
            event,
            context,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id=vid,
            resource_version=version,
        )


class ExtractionCompletedSearchIndexHandler(EventHandler):
    handler_name = "extraction_completed_search_index_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.DOCUMENT_EXTRACTION_COMPLETED:
            return
        payload = event.payload or {}
        eid = str(payload.get("extraction_id") or "").strip()
        version = int(payload.get("document_version") or 1)
        _enqueue_index(
            event,
            context,
            resource_type=SearchResourceTypes.DOCUMENT_TEXT_EXTRACTION,
            resource_id=eid,
            resource_version=version,
        )
        # Réindexe aussi le document Vault lié
        vid = str(payload.get("vault_document_id") or "").strip()
        if vid:
            _enqueue_index(
                event,
                context,
                resource_type=SearchResourceTypes.VAULT_DOCUMENT,
                resource_id=vid,
                resource_version=version,
            )


class AnalysisCompletedSearchIndexHandler(EventHandler):
    handler_name = "analysis_completed_search_index_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.DOCUMENT_ANALYSIS_COMPLETED:
            return
        payload = event.payload or {}
        aid = str(payload.get("analysis_id") or "").strip()
        version = int(payload.get("document_version") or 1)
        _enqueue_index(
            event,
            context,
            resource_type=SearchResourceTypes.DOCUMENT_ANALYSIS,
            resource_id=aid,
            resource_version=version,
        )


class AccountingProposalSearchIndexHandler(EventHandler):
    handler_name = "accounting_proposal_search_index_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name not in (
            EventNames.ACCOUNTING_PROPOSAL_READY,
            EventNames.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
            EventNames.ACCOUNTING_PROPOSAL_UPDATED,
            EventNames.ACCOUNTING_PROPOSAL_VALIDATED,
            EventNames.ACCOUNTING_PROPOSAL_REJECTED,
        ):
            return
        payload = event.payload or {}
        pid = str(payload.get("proposal_id") or "").strip()
        version = int(payload.get("document_version") or 1)
        _enqueue_index(
            event,
            context,
            resource_type=SearchResourceTypes.ACCOUNTING_PROPOSAL,
            resource_id=pid,
            resource_version=version,
        )
        entry_id = str(payload.get("entry_id") or "").strip()
        if entry_id:
            _enqueue_index(
                event,
                context,
                resource_type=SearchResourceTypes.ACCOUNTING_ENTRY,
                resource_id=entry_id,
                resource_version=1,
            )


class SalesCrmSearchIndexHandler(EventHandler):
    """Index Lead / Company / Opportunity / Activity / Task after CRM mutations."""

    handler_name = "sales_crm_search_index_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        payload = event.payload or {}
        mapping = {
            EventNames.SALES_LEAD_CREATED: (
                SearchResourceTypes.SALES_LEAD,
                str(payload.get("lead_id") or ""),
            ),
            EventNames.SALES_COMPANY_CREATED: (
                SearchResourceTypes.SALES_COMPANY,
                str(payload.get("company_id") or ""),
            ),
            EventNames.SALES_PERSON_CREATED: (
                SearchResourceTypes.SALES_PERSON,
                str(payload.get("person_id") or ""),
            ),
            EventNames.SALES_OPPORTUNITY_CREATED: (
                SearchResourceTypes.SALES_OPPORTUNITY,
                str(payload.get("opportunity_id") or ""),
            ),
            EventNames.SALES_OPPORTUNITY_UPDATED: (
                SearchResourceTypes.SALES_OPPORTUNITY,
                str(payload.get("opportunity_id") or ""),
            ),
            EventNames.SALES_OPPORTUNITY_STAGE_CHANGED: (
                SearchResourceTypes.SALES_OPPORTUNITY,
                str(payload.get("opportunity_id") or ""),
            ),
            EventNames.SALES_ACTIVITY_CREATED: (
                SearchResourceTypes.SALES_ACTIVITY,
                str(payload.get("activity_id") or ""),
            ),
            EventNames.SALES_TASK_CREATED: (
                SearchResourceTypes.SALES_TASK,
                str(payload.get("task_id") or ""),
            ),
            EventNames.SALES_TASK_COMPLETED: (
                SearchResourceTypes.SALES_TASK,
                str(payload.get("task_id") or ""),
            ),
        }
        pair = mapping.get(event.event_name)
        if not pair:
            return
        resource_type, resource_id = pair
        _enqueue_index(
            event,
            context,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_version=1,
        )
