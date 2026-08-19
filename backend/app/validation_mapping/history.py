"""Historique append-only."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.validation_mapping.models import ElfisValidationHistory


def append_history(
    db: Session,
    *,
    organization_id: int,
    validation_session_id: str,
    field_path: str,
    old_value: Any,
    new_value: Any,
    action: str,
    actor_user_id: int | None,
    reason: str | None = None,
    commit: bool = False,
) -> ElfisValidationHistory:
    row = ElfisValidationHistory(
        id=str(uuid4()),
        organization_id=organization_id,
        validation_session_id=validation_session_id,
        field_path=field_path,
        old_value=old_value,
        new_value=new_value,
        action=action,
        reason=reason,
        actor_user_id=actor_user_id,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def list_history(
    db: Session, *, organization_id: int, validation_session_id: str
) -> list[ElfisValidationHistory]:
    return (
        db.query(ElfisValidationHistory)
        .filter(ElfisValidationHistory.organization_id == organization_id)
        .filter(ElfisValidationHistory.validation_session_id == validation_session_id)
        .order_by(ElfisValidationHistory.created_at.asc())
        .all()
    )
