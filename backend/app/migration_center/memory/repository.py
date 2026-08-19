"""Repository Migration Memory — isolation organisation."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.migration_center.models import ElfisMigrationMemoryEntry


class MigrationMemoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, row: ElfisMigrationMemoryEntry, *, commit: bool = True) -> ElfisMigrationMemoryEntry:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def get_for_org(self, entry_id: str, organization_id: int) -> ElfisMigrationMemoryEntry | None:
        row = self._db.get(ElfisMigrationMemoryEntry, entry_id)
        if not row or row.organization_id != organization_id:
            return None
        return row

    def list_for_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        limit: int = 100,
    ) -> list[ElfisMigrationMemoryEntry]:
        return (
            self._db.query(ElfisMigrationMemoryEntry)
            .filter(ElfisMigrationMemoryEntry.organization_id == organization_id)
            .filter(ElfisMigrationMemoryEntry.migration_session_id == migration_session_id)
            .order_by(ElfisMigrationMemoryEntry.created_at.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def create(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        scope: str,
        memory_type: str,
        key_hash: str,
        payload: dict,
        source: str,
        status: str,
        confidence: float | None,
        created_by_user_id: int | None,
        commit: bool = True,
    ) -> ElfisMigrationMemoryEntry:
        row = ElfisMigrationMemoryEntry(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            scope=scope,
            memory_type=memory_type,
            key_hash=key_hash,
            payload=payload or {},
            confidence=confidence,
            source=source,
            status=status,
            created_by_user_id=created_by_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return self.add(row, commit=commit)
