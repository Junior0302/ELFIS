"""Publication d'événements métier Migration via Event Bus existant."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.migration_center.models import ElfisMigrationSession

logger = logging.getLogger(__name__)

# Mapping type logique → EventNames (.v1)
_EVENT_MAP: dict[str, str] = {
    "migration.session.created": EventNames.MIGRATION_SESSION_CREATED,
    "migration.profile.updated": EventNames.MIGRATION_PROFILE_UPDATED,
    "migration.sources.updated": EventNames.MIGRATION_SOURCES_UPDATED,
    "migration.step.started": EventNames.MIGRATION_STEP_STARTED,
    "migration.step.completed": EventNames.MIGRATION_STEP_COMPLETED,
    "migration.session.resumed": EventNames.MIGRATION_SESSION_RESUMED,
    "migration.session.cancelled": EventNames.MIGRATION_SESSION_CANCELLED,
    "migration.progress.updated": EventNames.MIGRATION_PROGRESS_UPDATED,
    "migration.activity.recorded": EventNames.MIGRATION_ACTIVITY_RECORDED,
}


def publish_migration_event(
    db: Session,
    *,
    event_type: str,
    session: ElfisMigrationSession,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> None:
    event_name = _EVENT_MAP.get(event_type, event_type)
    if not event_name.endswith(".v1") and event_type in _EVENT_MAP:
        event_name = _EVENT_MAP[event_type]

    event_id = str(uuid4())
    occurred_at = datetime.utcnow().isoformat() + "Z"
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "organization_id": session.organization_id,
        "migration_session_id": session.id,
        "migration_session_token": session.migration_session_token,
        "actor_user_id": actor_user_id,
        "occurred_at": occurred_at,
        "schema_version": 1,
        "metadata": dict(metadata or {}),
    }
    # Jamais de profils / fichiers / PII dans le payload
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=int(session.organization_id),
            aggregate_type="migration_session",
            aggregate_id=session.id,
            payload=payload,
            metadata={"source": "migration_center"},
            correlation_id=uuid4(),
            idempotency_key=(idempotency_key or f"{event_name}:{session.organization_id}:{session.id}:{event_id}")[
                :255
            ],
        ),
        commit=True,
    )
