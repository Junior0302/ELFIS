"""Event Bus ↔ Accounting Pipeline."""

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
from app.accounting.accounting_types import SUPPORTED_DOCUMENT_TYPES_V1, normalize_document_type

logger = logging.getLogger(__name__)


class DocumentAnalysisCompletedAccountingHandler(EventHandler):
    """document.analysis.completed.v1 → enqueue accounting.build_proposal.v1."""

    handler_name = "document_analysis_completed_accounting_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if not settings.elfis_auto_accounting_proposal_enabled:
            return
        if event.event_name != EventNames.DOCUMENT_ANALYSIS_COMPLETED:
            return
        payload = event.payload or {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        analysis_id = str(payload.get("analysis_id") or "").strip() or None
        if not vault_document_id:
            return
        doc_type = normalize_document_type(payload.get("document_type"))
        if doc_type not in SUPPORTED_DOCUMENT_TYPES_V1:
            return
        # status requires_review encore exploitable si extraction présente
        org_id = event.organization_id
        version = int(payload.get("document_version") or payload.get("version") or 1)
        idem = f"accounting-proposal:{org_id}:{vault_document_id}:{version}"
        try:
            JobService(context.db).enqueue(
                JobRequest(
                    job_name=JobNames.ACCOUNTING_BUILD_PROPOSAL,
                    organization_id=org_id,
                    user_id=_actor(event),
                    payload={
                        "vault_document_id": vault_document_id,
                        "document_analysis_id": analysis_id,
                        "document_version": version,
                    },
                    idempotency_key=idem,
                    correlation_id=str(event.correlation_id) if event.correlation_id else None,
                    causation_event_id=str(event.event_id),
                )
            )
        except Exception:
            logger.exception(
                "accounting_proposal_enqueue_failed",
                extra={
                    "vault_document_id": vault_document_id,
                    "organization_id": org_id,
                    "event_id": str(event.event_id),
                },
            )


def _actor(event: DomainEvent) -> int | None:
    raw = (event.metadata or {}).get("actor_user_id")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
