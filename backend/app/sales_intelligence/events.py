"""Sales Intelligence — Event Bus helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.sales_intelligence.models import SalesInsightItem


def publish_insight_event(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    insight: SalesInsightItem,
    actor_user_id: int | None = None,
    idempotency_key: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "insight_id": insight.id,
        "organization_id": organization_id,
        "insight_type": insight.insight_type,
        "category": insight.category,
        "severity": insight.severity,
        "source_type": insight.source_type,
        "source_id": insight.source_id,
        "linked_decision_id": insight.linked_decision_id,
        "status": insight.status,
    }
    if extra:
        payload.update(extra)
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type="sales_insight",
            aggregate_id=str(insight.id),
            payload=payload,
            metadata={
                "source": "sales_intelligence",
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
            },
            idempotency_key=idempotency_key
            or f"sales:insight:{event_name}:{insight.id}:{insight.status}",
        ),
        commit=False,
    )
