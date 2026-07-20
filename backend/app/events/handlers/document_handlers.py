"""Handlers métier liés aux documents / Vault."""

from __future__ import annotations

import logging

from app.events.event_context import EventContext, log_event
from app.events.event_registry import EventHandler
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.exceptions import EventHandlerError
from app.models_vault import VaultActivityLog, VaultDocument
from app.repositories.vault_repository import VaultRepository
from app.schemas_vault import VaultActivityAction

logger = logging.getLogger(__name__)


class DocumentArchivedAuditHandler(EventHandler):
    """
    Premier handler réel V1 — audit léger uniquement.
    N'envoie pas d'e-mail et n'appelle aucun service externe.
    """

    handler_name = "document_archived_audit_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.VAULT_DOCUMENT_ARCHIVED:
            raise EventHandlerError(
                f"Handler incompatible avec {event.event_name}",
                retryable=False,
            )

        payload = event.payload or {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            raise EventHandlerError("vault_document_id manquant", retryable=False)

        archive_status = str(payload.get("archive_status") or "").strip()
        if archive_status and archive_status != "archived":
            raise EventHandlerError(
                f"archive_status inattendu: {archive_status}",
                retryable=False,
            )

        log_event(
            logging.INFO,
            "document_archived_audit",
            event_id=str(event.event_id),
            event_name=event.event_name,
            handler_name=self.handler_name,
            organization_id=event.organization_id,
            correlation_id=str(event.correlation_id),
            attempt_count=context.attempt_count,
            worker_id=context.worker_id,
            status="ok",
            extra={
                "vault_document_id": vault_document_id,
                "business_document_type": payload.get("business_document_type"),
                "reused_existing_archive": bool(payload.get("reused_existing_archive")),
            },
        )

        db = context.db
        doc = (
            db.query(VaultDocument)
            .filter(
                VaultDocument.id == vault_document_id,
                VaultDocument.organization_id == event.organization_id,
            )
            .first()
        )
        if not doc:
            # Document peut être absent en tests unitaires purs — log only
            return

        existing = (
            db.query(VaultActivityLog)
            .filter(
                VaultActivityLog.organization_id == event.organization_id,
                VaultActivityLog.document_id == vault_document_id,
                VaultActivityLog.action == VaultActivityAction.document_archived.value,
            )
            .first()
        )
        if existing:
            return

        actor = None
        meta = event.metadata or {}
        raw_actor = meta.get("actor_user_id")
        if raw_actor is not None and str(raw_actor).isdigit():
            actor = int(raw_actor)

        repo = VaultRepository(db)
        repo.create_activity_log(
            organization_id=event.organization_id,
            document_id=vault_document_id,
            user_id=actor,
            action=VaultActivityAction.document_archived,
            metadata={
                "source": "event_bus",
                "event_id": str(event.event_id),
                "document_type": payload.get("document_type"),
                "business_document_id": payload.get("business_document_id"),
            },
        )
