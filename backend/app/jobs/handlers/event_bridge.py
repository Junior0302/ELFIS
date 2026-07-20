"""Handler Event Bus → enqueue metadata job (optionnel)."""

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

logger = logging.getLogger(__name__)


class DocumentArchivedMetadataJobHandler(EventHandler):
    """
    Écoute vault.document.archived.v1 et enqueue vault.document.metadata_check.v1.

    - activé par ELFIS_VAULT_METADATA_JOB_ENABLED
    - n'archive pas / ne télécharge pas / n'appelle pas l'IA
    - idempotent via idempotency_key
    - ne doit jamais bloquer l'archivage (erreurs avalées)
    """

    handler_name = "document_archived_metadata_job_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if not settings.elfis_vault_metadata_job_enabled:
            return
        if event.event_name != EventNames.VAULT_DOCUMENT_ARCHIVED:
            return

        payload = event.payload or {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            return

        org_id = event.organization_id
        expected_type = str(payload.get("document_type") or "").strip() or None
        idem = f"vault-metadata-check:{org_id}:{vault_document_id}"

        try:
            JobService(context.db).enqueue(
                JobRequest(
                    job_name=JobNames.VAULT_DOCUMENT_METADATA_CHECK,
                    organization_id=org_id,
                    user_id=_actor_user_id(event),
                    queue_name="default",
                    payload={
                        "vault_document_id": vault_document_id,
                        **(
                            {"expected_document_type": expected_type}
                            if expected_type
                            else {}
                        ),
                    },
                    idempotency_key=idem,
                    correlation_id=str(event.correlation_id) if event.correlation_id else None,
                    causation_event_id=str(event.event_id),
                )
            )
        except Exception:
            logger.exception(
                "vault_metadata_job_enqueue_failed",
                extra={
                    "vault_document_id": vault_document_id,
                    "organization_id": org_id,
                    "event_id": str(event.event_id),
                },
            )


def _actor_user_id(event: DomainEvent) -> int | None:
    meta = event.metadata or {}
    raw = meta.get("actor_user_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
