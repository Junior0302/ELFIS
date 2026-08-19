"""Feedback utilisateur — utile / inutile / incorrect."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai_assistant.events import publish_feedback
from app.ai_assistant.models import ElfisAssistantFeedback, ElfisAssistantMessage
from app.ai_assistant.types import FeedbackKind


def record_feedback(
    db: Session,
    *,
    organization_id: int,
    user_id: int,
    message_id: str,
    kind: str,
    comment: str = "",
) -> ElfisAssistantFeedback:
    try:
        FeedbackKind(kind)
    except ValueError as exc:
        raise ValueError("kind doit être useful, useless ou incorrect") from exc

    message = (
        db.query(ElfisAssistantMessage)
        .filter(
            ElfisAssistantMessage.id == message_id,
            ElfisAssistantMessage.organization_id == organization_id,
        )
        .first()
    )
    if message is None:
        raise LookupError("Message introuvable")

    row = ElfisAssistantFeedback(
        organization_id=organization_id,
        user_id=user_id,
        message_id=message_id,
        kind=kind,
        comment=(comment or "")[:2000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        publish_feedback(
            db,
            organization_id=organization_id,
            feedback_id=row.id,
            message_id=message_id,
            kind=kind,
        )
    except Exception:
        pass
    return row
