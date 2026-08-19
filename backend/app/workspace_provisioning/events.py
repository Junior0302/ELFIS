"""Publication d’événements provisioning (sans données sensibles)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.workspace_provisioning.steps import PROVISIONING_VERSION


def _payload(organization_id: int, user_id: int, step: str) -> dict:
    return {
        "organization_id": organization_id,
        "user_id": user_id,
        "provisioning_version": PROVISIONING_VERSION,
        "step": step,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def publish_provision_event(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    user_id: int,
    step: str,
    idempotency_key: str | None = None,
) -> None:
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type="workspace_provisioning",
            aggregate_id=str(organization_id),
            payload=_payload(organization_id, user_id, step),
            idempotency_key=idempotency_key,
        ),
        commit=False,
    )


# Re-export names used by service for clarity
EVENT_STARTED = EventNames.WORKSPACE_PROVISION_STARTED
EVENT_PROFILE = EventNames.WORKSPACE_PROVISION_COMPANY_PROFILE_SAVED
EVENT_SETTINGS = EventNames.WORKSPACE_PROVISION_SETTINGS_CONFIGURED
EVENT_COMPLETED = EventNames.WORKSPACE_PROVISION_COMPLETED
EVENT_FAILED = EventNames.WORKSPACE_PROVISION_FAILED
