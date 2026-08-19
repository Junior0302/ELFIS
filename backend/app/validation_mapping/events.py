"""Événements Validation & Mapping."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.validation_mapping.models import ElfisValidationSession


def _map(event_type: str) -> str:
    return {
        "validation.started": EventNames.VALIDATION_STARTED,
        "field.edited": EventNames.VALIDATION_FIELD_EDITED,
        "field.accepted": EventNames.VALIDATION_FIELD_ACCEPTED,
        "document.validated": EventNames.VALIDATION_DOCUMENT_VALIDATED,
        "document.rejected": EventNames.VALIDATION_DOCUMENT_REJECTED,
        "duplicate.detected": EventNames.VALIDATION_DUPLICATE_DETECTED,
        "matching.completed": EventNames.VALIDATION_MATCHING_COMPLETED,
        "ready_for_import": EventNames.VALIDATION_READY_FOR_IMPORT,
    }.get(event_type, event_type)


def publish_validation_event(
    db: Session,
    *,
    event_type: str,
    session: ElfisValidationSession,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> None:
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": session.organization_id,
        "migration_session_id": session.migration_session_id,
        "document_intake_item_id": session.document_intake_item_id,
        "universal_document_id": session.universal_document_id,
        "validation_session_id": session.id,
        "extraction_id": session.extraction_id,
        "status": session.status,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "schema_version_event": 1,
        "metadata": {
            k: v
            for k, v in (metadata or {}).items()
            if k
            in {
                "field_path",
                "action",
                "duplicate_count",
                "match_count",
                "error_code",
                "progress_percent",
            }
        },
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(session.organization_id),
            aggregate_type="validation_mapping",
            aggregate_id=session.id,
            payload=payload,
            metadata={"source": "validation_mapping"},
            correlation_id=uuid4(),
            idempotency_key=(
                f"{event_type}:{session.organization_id}:{session.id}:{session.version}"
            )[:255],
        ),
        commit=commit,
    )
