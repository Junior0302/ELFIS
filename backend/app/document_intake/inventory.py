"""Inventaire — helpers de lecture / agrégats."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.document_intake.models import ElfisDocumentIntakeItem


def inventory_summary(db: Session, *, organization_id: int, migration_session_id: str | None = None) -> dict[str, Any]:
    q = db.query(ElfisDocumentIntakeItem).filter(
        ElfisDocumentIntakeItem.organization_id == organization_id
    )
    if migration_session_id:
        q = q.filter(ElfisDocumentIntakeItem.migration_session_id == migration_session_id)
    items = q.all()
    by_status: dict[str, int] = {}
    total_bytes = 0
    duplicates = 0
    for it in items:
        by_status[it.status] = by_status.get(it.status, 0) + 1
        total_bytes += int(it.size_bytes or 0)
        if it.is_duplicate:
            duplicates += 1
    return {
        "count": len(items),
        "total_bytes": total_bytes,
        "duplicates": duplicates,
        "by_status": by_status,
    }
