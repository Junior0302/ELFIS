"""Audit Accounting Intelligence V2."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.accounting_intelligence.models import ElfisAiAudit


def write_intelligence_audit(
    db: Session,
    *,
    organization_id: int,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> ElfisAiAudit:
    row = ElfisAiAudit(
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        detail_json=detail or {},
    )
    db.add(row)
    db.flush()
    return row
