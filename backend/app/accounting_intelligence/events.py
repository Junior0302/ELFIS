"""Events Accounting Intelligence V2."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames


def _map(event_type: str) -> str:
    return {
        "learning.created": EventNames.ACCOUNTING_INTELLIGENCE_LEARNING_CREATED,
        "feedback.received": EventNames.ACCOUNTING_INTELLIGENCE_FEEDBACK_RECEIVED,
        "recommendation.generated": EventNames.ACCOUNTING_INTELLIGENCE_RECOMMENDATION_GENERATED,
        "recommendation.accepted": EventNames.ACCOUNTING_INTELLIGENCE_RECOMMENDATION_ACCEPTED,
        "recommendation.modified": EventNames.ACCOUNTING_INTELLIGENCE_RECOMMENDATION_MODIFIED,
        "recommendation.rejected": EventNames.ACCOUNTING_INTELLIGENCE_RECOMMENDATION_REJECTED,
    }.get(event_type, event_type)


def publish_intelligence_event(
    db: Session,
    *,
    event_type: str,
    organization_id: int,
    aggregate_id: str,
    actor_user_id: int | None = None,
    payload: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    body = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": organization_id,
        "aggregate_id": aggregate_id,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        **(payload or {}),
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(organization_id),
            aggregate_type="accounting_intelligence",
            aggregate_id=aggregate_id,
            payload=body,
            metadata={"source": "accounting_intelligence"},
            correlation_id=uuid4(),
            idempotency_key=f"{event_type}:{organization_id}:{aggregate_id}:{uuid4()}"[:255],
        ),
        commit=commit,
    )
