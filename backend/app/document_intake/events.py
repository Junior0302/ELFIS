"""Événements métier Document Intake via Event Bus."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_intake.models import ElfisDocumentIntakeItem, ElfisDocumentUploadSession
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames


def _name_map() -> dict[str, str]:
    return {
        "document.uploaded": EventNames.DOCUMENT_UPLOADED,
        "document.validated": EventNames.DOCUMENT_VALIDATED,
        "document.rejected": EventNames.DOCUMENT_REJECTED,
        "document.duplicate_detected": EventNames.DOCUMENT_DUPLICATE_DETECTED,
        "document.ready_for_analysis": EventNames.DOCUMENT_READY_FOR_ANALYSIS,
        "document.lifecycle.changed": EventNames.DOCUMENT_LIFECYCLE_CHANGED,
        "document.upload_session.created": EventNames.DOCUMENT_UPLOAD_SESSION_CREATED,
        "document.upload_session.started": EventNames.DOCUMENT_UPLOAD_SESSION_STARTED,
        "document.upload_session.paused": EventNames.DOCUMENT_UPLOAD_SESSION_PAUSED,
        "document.upload_session.resumed": EventNames.DOCUMENT_UPLOAD_SESSION_RESUMED,
        "document.upload_session.completed": EventNames.DOCUMENT_UPLOAD_SESSION_COMPLETED,
        "document.upload_session.cancelled": EventNames.DOCUMENT_UPLOAD_SESSION_CANCELLED,
        "document.upload.analytics.updated": EventNames.DOCUMENT_UPLOAD_ANALYTICS_UPDATED,
        "document.fingerprint.created": EventNames.DOCUMENT_FINGERPRINT_CREATED,
    }


def publish_intake_event(
    db: Session,
    *,
    event_type: str,
    item: ElfisDocumentIntakeItem,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    commit: bool = True,
) -> None:
    event_name = _name_map().get(event_type, event_type)
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": item.organization_id,
        "document_intake_item_id": item.id,
        "intake_item_id": item.id,
        "intake_token": item.intake_token,
        "universal_document_id": item.universal_document_id,
        "migration_session_id": item.migration_session_id,
        "upload_session_id": item.upload_session_id,
        "checksum_sha256": item.checksum_sha256,
        "status": item.status,
        "lifecycle_status": item.lifecycle_status or item.status,
        "format_id": item.format_id,
        "size_bytes": item.size_bytes,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": 1,
        "metadata": dict(metadata or {}),
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=int(item.organization_id),
            aggregate_type="document_intake_item",
            aggregate_id=item.id,
            payload=payload,
            metadata={"source": "document_intake"},
            correlation_id=uuid4(),
            idempotency_key=(
                idempotency_key or f"{event_name}:{item.organization_id}:{item.id}"
            )[:255],
        ),
        commit=commit,
    )


def publish_upload_session_event(
    db: Session,
    *,
    event_type: str,
    session: ElfisDocumentUploadSession,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    commit: bool = True,
) -> None:
    event_name = _name_map().get(event_type, event_type)
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": session.organization_id,
        "migration_session_id": session.migration_session_id,
        "upload_session_id": session.id,
        "document_intake_item_id": None,
        "universal_document_id": None,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": 1,
        "metadata": {
            "status": session.status,
            "display_label": session.display_label,
            **dict(metadata or {}),
        },
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=int(session.organization_id),
            aggregate_type="document_upload_session",
            aggregate_id=session.id,
            payload=payload,
            metadata={"source": "document_intake"},
            correlation_id=uuid4(),
            idempotency_key=(
                idempotency_key or f"{event_name}:{session.organization_id}:{session.id}"
            )[:255],
        ),
        commit=commit,
    )
