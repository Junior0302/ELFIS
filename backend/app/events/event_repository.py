"""Persistance Event Bus."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.events.event_models import ElfisEvent, ElfisEventDelivery
from app.events.event_schemas import DeliveryStatus, DomainEvent, EventStatus
from app.events.exceptions import EventDuplicateError, EventPublishError


class EventRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_by_idempotency_key(self, key: str) -> ElfisEvent | None:
        if not key:
            return None
        return (
            self._db.query(ElfisEvent)
            .filter(ElfisEvent.idempotency_key == key)
            .order_by(ElfisEvent.created_at.asc())
            .first()
        )

    def find_by_event_id(self, event_id: str) -> ElfisEvent | None:
        return self._db.query(ElfisEvent).filter(ElfisEvent.event_id == event_id).first()

    def create_event_with_deliveries(
        self,
        event: DomainEvent,
        handler_names: list[str],
        *,
        max_attempts: int = 5,
        priority: int = 100,
        commit: bool = True,
    ) -> ElfisEvent:
        if event.idempotency_key:
            existing = self.find_by_idempotency_key(event.idempotency_key)
            if existing:
                raise EventDuplicateError(
                    "Événement déjà publié (idempotency_key)",
                    existing_event_id=existing.event_id,
                )

        now = datetime.utcnow()
        row = ElfisEvent(
            id=str(uuid.uuid4()),
            event_id=str(event.event_id),
            event_name=event.event_name,
            event_version=event.event_version,
            organization_id=event.organization_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=dict(event.payload or {}),
            metadata_json=dict(event.metadata or {}),
            status=EventStatus.pending.value,
            priority=priority,
            attempt_count=0,
            max_attempts=max_attempts,
            available_at=now,
            idempotency_key=event.idempotency_key,
            correlation_id=str(event.correlation_id),
            causation_id=str(event.causation_id) if event.causation_id else None,
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        for handler_name in handler_names:
            self._db.add(
                ElfisEventDelivery(
                    id=str(uuid.uuid4()),
                    event_id=row.event_id,
                    handler_name=handler_name,
                    status=DeliveryStatus.pending.value,
                    attempt_count=0,
                    created_at=now,
                    updated_at=now,
                )
            )
        try:
            if commit:
                self._db.commit()
                self._db.refresh(row)
            else:
                self._db.flush()
        except EventDuplicateError:
            raise
        except Exception as exc:
            self._db.rollback()
            # Collision unique possible (idempotency / event_id)
            if event.idempotency_key:
                again = self.find_by_idempotency_key(event.idempotency_key)
                if again:
                    raise EventDuplicateError(
                        "Événement déjà publié (idempotency_key)",
                        existing_event_id=again.event_id,
                    ) from exc
            raise EventPublishError("Échec de persistance de l'événement") from exc
        return row

    def list_deliveries(self, event_id: str) -> list[ElfisEventDelivery]:
        return (
            self._db.query(ElfisEventDelivery)
            .filter(ElfisEventDelivery.event_id == event_id)
            .order_by(ElfisEventDelivery.created_at.asc())
            .all()
        )

    def claim_events(
        self,
        *,
        worker_id: str,
        batch_size: int,
        lock_timeout_seconds: int,
    ) -> list[ElfisEvent]:
        """Réserve un lot d'événements (transaction courte)."""
        now = datetime.utcnow()
        lock_expired_before = now - timedelta(seconds=max(30, lock_timeout_seconds))
        dialect = self._db.bind.dialect.name if self._db.bind is not None else "sqlite"

        if dialect == "postgresql":
            return self._claim_events_postgres(
                worker_id=worker_id,
                batch_size=batch_size,
                now=now,
                lock_expired_before=lock_expired_before,
            )
        return self._claim_events_sqlite(
            worker_id=worker_id,
            batch_size=batch_size,
            now=now,
            lock_expired_before=lock_expired_before,
        )

    def _claim_events_postgres(
        self,
        *,
        worker_id: str,
        batch_size: int,
        now: datetime,
        lock_expired_before: datetime,
    ) -> list[ElfisEvent]:
        sql = text(
            """
            SELECT id FROM elfis_events
            WHERE (
                (status IN ('pending', 'retry') AND available_at <= :now)
                OR (
                    status = 'processing'
                    AND locked_at IS NOT NULL
                    AND locked_at < :lock_expired_before
                )
            )
            ORDER BY priority ASC, available_at ASC, created_at ASC
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
            """
        )
        ids = [
            row[0]
            for row in self._db.execute(
                sql,
                {
                    "now": now,
                    "lock_expired_before": lock_expired_before,
                    "batch_size": batch_size,
                },
            ).fetchall()
        ]
        if not ids:
            return []
        rows = (
            self._db.query(ElfisEvent)
            .filter(ElfisEvent.id.in_(ids))
            .order_by(ElfisEvent.priority.asc(), ElfisEvent.available_at.asc())
            .all()
        )
        for row in rows:
            row.status = EventStatus.processing.value
            row.locked_at = now
            row.locked_by = worker_id
            row.updated_at = now
        self._db.commit()
        for row in rows:
            self._db.refresh(row)
        return rows

    def _claim_events_sqlite(
        self,
        *,
        worker_id: str,
        batch_size: int,
        now: datetime,
        lock_expired_before: datetime,
    ) -> list[ElfisEvent]:
        candidates = (
            self._db.query(ElfisEvent)
            .filter(
                or_(
                    and_(
                        ElfisEvent.status.in_(
                            [EventStatus.pending.value, EventStatus.retry.value]
                        ),
                        ElfisEvent.available_at <= now,
                    ),
                    and_(
                        ElfisEvent.status == EventStatus.processing.value,
                        ElfisEvent.locked_at.isnot(None),
                        ElfisEvent.locked_at < lock_expired_before,
                    ),
                )
            )
            .order_by(
                ElfisEvent.priority.asc(),
                ElfisEvent.available_at.asc(),
                ElfisEvent.created_at.asc(),
            )
            .limit(batch_size)
            .all()
        )
        claimed: list[ElfisEvent] = []
        for row in candidates:
            # Verrou optimiste simplifié SQLite
            updated = (
                self._db.query(ElfisEvent)
                .filter(
                    ElfisEvent.id == row.id,
                    or_(
                        ElfisEvent.status.in_(
                            [EventStatus.pending.value, EventStatus.retry.value]
                        ),
                        and_(
                            ElfisEvent.status == EventStatus.processing.value,
                            ElfisEvent.locked_at < lock_expired_before,
                        ),
                    ),
                )
                .update(
                    {
                        ElfisEvent.status: EventStatus.processing.value,
                        ElfisEvent.locked_at: now,
                        ElfisEvent.locked_by: worker_id,
                        ElfisEvent.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                claimed.append(row)
        self._db.commit()
        result: list[ElfisEvent] = []
        for row in claimed:
            refreshed = self.find_by_event_id(row.event_id)
            if refreshed and refreshed.locked_by == worker_id:
                result.append(refreshed)
        return result

    def save_delivery(self, delivery: ElfisEventDelivery, *, commit: bool = True) -> None:
        delivery.updated_at = datetime.utcnow()
        self._db.add(delivery)
        if commit:
            self._db.commit()
            self._db.refresh(delivery)

    def save_event(self, event: ElfisEvent, *, commit: bool = True) -> None:
        event.updated_at = datetime.utcnow()
        self._db.add(event)
        if commit:
            self._db.commit()
            self._db.refresh(event)

    def list_events(
        self,
        *,
        status: str | None = None,
        event_name: str | None = None,
        organization_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisEvent], int]:
        q = self._db.query(ElfisEvent)
        if status:
            q = q.filter(ElfisEvent.status == status)
        if event_name:
            q = q.filter(ElfisEvent.event_name == event_name)
        if organization_id is not None:
            q = q.filter(ElfisEvent.organization_id == organization_id)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def to_domain(self, row: ElfisEvent) -> DomainEvent:
        return DomainEvent(
            event_id=uuid.UUID(row.event_id),
            event_name=row.event_name,
            event_version=row.event_version,
            organization_id=row.organization_id,
            aggregate_type=row.aggregate_type,
            aggregate_id=row.aggregate_id,
            payload=dict(row.payload or {}),
            metadata=dict(row.metadata_json or {}),
            idempotency_key=row.idempotency_key,
            correlation_id=uuid.UUID(row.correlation_id)
            if row.correlation_id
            else uuid.uuid4(),
            causation_id=uuid.UUID(row.causation_id) if row.causation_id else None,
            occurred_at=row.created_at or datetime.utcnow(),
        )
