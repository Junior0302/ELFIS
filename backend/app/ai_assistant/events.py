"""Événements AI Financial Assistant pour le bus plateforme."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames


def _publish(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict,
    idempotency_key: str,
) -> None:
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            metadata={"source": "ai_financial_assistant_v1"},
            idempotency_key=idempotency_key,
            correlation_id=uuid.uuid4(),
        ),
    )


def publish_chat_completed(
    db: Session,
    *,
    organization_id: int,
    message_id: str,
    tools_used: list[str],
    confidence: str,
    latency_ms: float,
) -> None:
    _publish(
        db,
        event_name=EventNames.AI_ASSISTANT_CHAT_COMPLETED,
        organization_id=organization_id,
        aggregate_type="assistant_message",
        aggregate_id=message_id,
        payload={
            "message_id": message_id,
            "tools_used": tools_used,
            "confidence": confidence,
            "latency_ms": latency_ms,
        },
        idempotency_key=f"assistant-chat-{message_id}",
    )


def publish_feedback(
    db: Session,
    *,
    organization_id: int,
    feedback_id: str,
    message_id: str,
    kind: str,
) -> None:
    _publish(
        db,
        event_name=EventNames.AI_ASSISTANT_FEEDBACK_RECORDED,
        organization_id=organization_id,
        aggregate_type="assistant_feedback",
        aggregate_id=feedback_id,
        payload={"feedback_id": feedback_id, "message_id": message_id, "kind": kind},
        idempotency_key=f"assistant-feedback-{feedback_id}",
    )
