"""Repository Migration Center."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.migration_center.enums import MigrationMode, TERMINAL_INACTIVE
from app.migration_center.models import ElfisMigrationSession


class MigrationCenterRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, session_id: str) -> ElfisMigrationSession | None:
        return self._db.get(ElfisMigrationSession, session_id)

    def get_by_session_token(
        self, organization_id: int, migration_session_token: str
    ) -> ElfisMigrationSession | None:
        return (
            self._db.query(ElfisMigrationSession)
            .filter(ElfisMigrationSession.organization_id == organization_id)
            .filter(ElfisMigrationSession.migration_session_token == migration_session_token)
            .first()
        )

    def add(self, row: ElfisMigrationSession, *, commit: bool = True) -> ElfisMigrationSession:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save(self, row: ElfisMigrationSession, *, commit: bool = True) -> ElfisMigrationSession:
        row.updated_at = datetime.utcnow()
        row.last_activity_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_sessions(
        self,
        *,
        organization_id: int,
        status: str | None = None,
        mode: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ElfisMigrationSession], int]:
        q = self._db.query(ElfisMigrationSession).filter(
            ElfisMigrationSession.organization_id == organization_id
        )
        if status:
            q = q.filter(ElfisMigrationSession.status == status)
        if mode:
            q = q.filter(ElfisMigrationSession.mode == mode)
        total = q.count()
        items = (
            q.order_by(ElfisMigrationSession.last_activity_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def find_active_initial(self, organization_id: int) -> ElfisMigrationSession | None:
        q = (
            self._db.query(ElfisMigrationSession)
            .filter(ElfisMigrationSession.organization_id == organization_id)
            .filter(ElfisMigrationSession.mode == MigrationMode.INITIAL_MIGRATION.value)
            .filter(~ElfisMigrationSession.status.in_(list(TERMINAL_INACTIVE)))
            .order_by(ElfisMigrationSession.created_at.desc())
        )
        return q.first()

    def token_exists(self, token: str) -> bool:
        return (
            self._db.query(ElfisMigrationSession.id)
            .filter(ElfisMigrationSession.migration_session_token == token)
            .first()
            is not None
        )
