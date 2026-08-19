"""MigrationTimelineService — historique structuré des étapes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.migration_center.enums import (
    TIMELINE_STEP_ORDER,
    TimelineEntryStatus,
    TimelineStepKey,
)
from app.migration_center.models import ElfisMigrationTimelineEntry

logger = logging.getLogger(__name__)


class MigrationTimelineService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _get_entry(
        self, *, organization_id: int, migration_session_id: str, step_key: str
    ) -> ElfisMigrationTimelineEntry | None:
        return (
            self._db.query(ElfisMigrationTimelineEntry)
            .filter(ElfisMigrationTimelineEntry.organization_id == organization_id)
            .filter(ElfisMigrationTimelineEntry.migration_session_id == migration_session_id)
            .filter(ElfisMigrationTimelineEntry.step_key == step_key)
            .first()
        )

    def ensure_entry(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        step_key: str,
        status: str = TimelineEntryStatus.PENDING.value,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> ElfisMigrationTimelineEntry:
        existing = self._get_entry(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=step_key,
        )
        if existing:
            return existing
        row = ElfisMigrationTimelineEntry(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=step_key,
            step_order=int(TIMELINE_STEP_ORDER.get(step_key, 0)),
            status=status,
            metadata_json=dict(metadata or {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def start_step(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        step_key: str,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> ElfisMigrationTimelineEntry:
        row = self.ensure_entry(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=step_key,
            status=TimelineEntryStatus.PENDING.value,
            metadata=metadata,
            commit=False,
        )
        # Idempotent : déjà started/completed → ne pas redémarrer
        if row.status in (
            TimelineEntryStatus.STARTED.value,
            TimelineEntryStatus.COMPLETED.value,
            TimelineEntryStatus.FAILED.value,
            TimelineEntryStatus.CANCELLED.value,
        ):
            return row
        now = datetime.utcnow()
        row.status = TimelineEntryStatus.STARTED.value
        row.started_at = now
        row.updated_at = now
        if metadata:
            meta = dict(row.metadata_json or {})
            meta.update(metadata)
            row.metadata_json = meta
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        logger.info(
            "migration_step_started",
            extra={
                "organization_id": organization_id,
                "migration_session_id": migration_session_id,
                "operation": "start_step",
                "status": "started",
                "step_key": step_key,
            },
        )
        return row

    def complete_step(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        step_key: str,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> ElfisMigrationTimelineEntry:
        row = self.ensure_entry(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=step_key,
            status=TimelineEntryStatus.STARTED.value,
            commit=False,
        )
        if row.status == TimelineEntryStatus.COMPLETED.value:
            return row  # idempotent
        now = datetime.utcnow()
        if not row.started_at:
            row.started_at = now
        row.status = TimelineEntryStatus.COMPLETED.value
        row.completed_at = now
        if row.started_at:
            delta = now - row.started_at
            row.duration_ms = max(0, int(delta.total_seconds() * 1000))
        row.updated_at = now
        if metadata:
            meta = dict(row.metadata_json or {})
            meta.update(metadata)
            row.metadata_json = meta
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        logger.info(
            "migration_step_completed",
            extra={
                "organization_id": organization_id,
                "migration_session_id": migration_session_id,
                "operation": "complete_step",
                "status": "completed",
                "step_key": step_key,
                "duration_ms": row.duration_ms,
            },
        )
        return row

    def fail_step(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        step_key: str,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> ElfisMigrationTimelineEntry:
        row = self.ensure_entry(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=step_key,
            commit=False,
        )
        if row.status == TimelineEntryStatus.FAILED.value:
            return row
        now = datetime.utcnow()
        if not row.started_at:
            row.started_at = now
        row.status = TimelineEntryStatus.FAILED.value
        row.completed_at = now
        if row.started_at:
            row.duration_ms = max(0, int((now - row.started_at).total_seconds() * 1000))
        row.updated_at = now
        if metadata:
            meta = dict(row.metadata_json or {})
            meta.update(metadata)
            row.metadata_json = meta
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def cancel_step(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        step_key: str,
        commit: bool = False,
    ) -> ElfisMigrationTimelineEntry:
        row = self.ensure_entry(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=step_key,
            commit=False,
        )
        if row.status in (
            TimelineEntryStatus.CANCELLED.value,
            TimelineEntryStatus.COMPLETED.value,
        ):
            return row
        now = datetime.utcnow()
        row.status = TimelineEntryStatus.CANCELLED.value
        row.completed_at = now
        if row.started_at:
            row.duration_ms = max(0, int((now - row.started_at).total_seconds() * 1000))
        row.updated_at = now
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_timeline(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
    ) -> list[ElfisMigrationTimelineEntry]:
        return (
            self._db.query(ElfisMigrationTimelineEntry)
            .filter(ElfisMigrationTimelineEntry.organization_id == organization_id)
            .filter(ElfisMigrationTimelineEntry.migration_session_id == migration_session_id)
            .order_by(ElfisMigrationTimelineEntry.step_order.asc(), ElfisMigrationTimelineEntry.created_at.asc())
            .all()
        )

    def get_current_step_entry(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
    ) -> ElfisMigrationTimelineEntry | None:
        started = (
            self._db.query(ElfisMigrationTimelineEntry)
            .filter(ElfisMigrationTimelineEntry.organization_id == organization_id)
            .filter(ElfisMigrationTimelineEntry.migration_session_id == migration_session_id)
            .filter(ElfisMigrationTimelineEntry.status == TimelineEntryStatus.STARTED.value)
            .order_by(ElfisMigrationTimelineEntry.step_order.desc())
            .first()
        )
        if started:
            return started
        return (
            self._db.query(ElfisMigrationTimelineEntry)
            .filter(ElfisMigrationTimelineEntry.organization_id == organization_id)
            .filter(ElfisMigrationTimelineEntry.migration_session_id == migration_session_id)
            .order_by(ElfisMigrationTimelineEntry.step_order.desc())
            .first()
        )

    def bootstrap_welcome(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        commit: bool = False,
    ) -> ElfisMigrationTimelineEntry:
        return self.start_step(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            step_key=TimelineStepKey.WELCOME.value,
            commit=commit,
        )
