"""Audit Accounting Engine V2."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.models import ElfisAccountingEngineAudit


def write_engine_audit(
    db: Session,
    *,
    organization_id: int,
    action: str,
    proposal_id: str | None = None,
    actor_user_id: int | None = None,
    detail: dict[str, Any] | None = None,
) -> ElfisAccountingEngineAudit:
    row = ElfisAccountingEngineAudit(
        organization_id=organization_id,
        proposal_id=proposal_id,
        action=action,
        actor_user_id=actor_user_id,
        detail_json=detail or {},
    )
    db.add(row)
    db.flush()
    return row
