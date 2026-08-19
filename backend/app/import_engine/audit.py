"""Audit Import Engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.import_engine.models import ElfisImportAuditLog


def write_import_audit(
    db: Session,
    *,
    organization_id: int,
    action: str,
    import_run_id: str | None = None,
    entity_kind: str | None = None,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    reason: str | None = None,
    detail: dict[str, Any] | None = None,
) -> ElfisImportAuditLog:
    """Audit append-only sans commit (compatible transaction d'import)."""
    row = ElfisImportAuditLog(
        organization_id=organization_id,
        import_run_id=import_run_id,
        action=action,
        entity_kind=entity_kind,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        reason=reason,
        detail_json=detail or {},
    )
    db.add(row)
    db.flush()
    return row
