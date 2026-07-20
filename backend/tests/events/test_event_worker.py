"""Tests Event Worker — retry, dead letter, locks, idempotence d'exécution."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_bus import DatabaseEventBus
from app.events.event_context import EventContext
from app.events.event_models import ElfisEvent, ElfisEventDelivery
from app.events.event_registry import EventHandler, EventHandlerRegistry
from app.events.event_schemas import DeliveryStatus, DomainEvent, EventStatus
from app.events.event_types import EventNames
from app.events.event_worker import EventWorker, compute_retry_delay_seconds
from app.events.exceptions import EventHandlerError


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class _SuccessHandler(EventHandler):
    handler_name = "success_handler_v1"

    def __init__(self):
        self.calls = 0

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        self.calls += 1


class _FlakyHandler(EventHandler):
    handler_name = "flaky_handler_v1"

    def __init__(self, fail_times: int = 2):
        self.fail_times = fail_times
        self.calls = 0

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise EventHandlerError("temporary outage", retryable=True)


class _AlwaysFailHandler(EventHandler):
    handler_name = "always_fail_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        raise EventHandlerError("permanent-ish fail", retryable=True)


def test_backoff_calculation():
    assert compute_retry_delay_seconds(1, base_seconds=10, jitter=False) == 10
    assert compute_retry_delay_seconds(2, base_seconds=10, jitter=False) == 30
    assert compute_retry_delay_seconds(3, base_seconds=10, jitter=False) == 90
    assert compute_retry_delay_seconds(4, base_seconds=10, jitter=False) == 270


def test_worker_processes_delivery_to_processed():
    db = _session()
    registry = EventHandlerRegistry()
    handler = _SuccessHandler()
    registry.register(EventNames.VAULT_DOCUMENT_ARCHIVED, handler)
    bus = DatabaseEventBus(db, registry=registry)
    row = bus.publish(
        DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
            organization_id=1,
            payload={"vault_document_id": "v1", "archive_status": "archived"},
            idempotency_key="w1",
        )
    )
    worker = EventWorker(db, registry=registry, worker_id="worker-a", batch_size=10)
    assert worker.process_next_batch() == 1
    delivery = db.query(ElfisEventDelivery).filter(ElfisEventDelivery.event_id == row.event_id).one()
    assert delivery.status == DeliveryStatus.processed.value
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    assert event.status == EventStatus.processed.value
    assert handler.calls == 1


def test_handler_retry_then_success():
    db = _session()
    registry = EventHandlerRegistry()
    handler = _FlakyHandler(fail_times=1)
    registry.register(EventNames.DELIVERY_EMAIL_STARTED, handler)
    bus = DatabaseEventBus(db, registry=registry, max_attempts=5)
    row = bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_STARTED,
            organization_id=1,
            payload={"business_document_id": "9"},
            idempotency_key="retry-1",
        )
    )
    worker = EventWorker(db, registry=registry, worker_id="w-retry")
    worker.process_next_batch()
    delivery = db.query(ElfisEventDelivery).filter(ElfisEventDelivery.event_id == row.event_id).one()
    assert delivery.status == DeliveryStatus.retry.value
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    assert event.status == EventStatus.retry.value
    assert event.available_at > datetime.utcnow()
    assert delivery.last_error
    assert "xkeysib" not in (delivery.last_error or "").lower()

    # Rendre disponible immédiatement
    event.available_at = datetime.utcnow() - timedelta(seconds=1)
    db.add(event)
    db.commit()
    worker.process_next_batch()
    delivery = db.query(ElfisEventDelivery).filter(ElfisEventDelivery.event_id == row.event_id).one()
    assert delivery.status == DeliveryStatus.processed.value
    assert handler.calls == 2


def test_max_attempts_dead_letter():
    db = _session()
    registry = EventHandlerRegistry()
    registry.register(EventNames.DELIVERY_EMAIL_FAILED, _AlwaysFailHandler())
    bus = DatabaseEventBus(db, registry=registry, max_attempts=2)
    row = bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_FAILED,
            organization_id=1,
            payload={"business_document_id": "1", "error_code": "x"},
            idempotency_key="dl-1",
        )
    )
    worker = EventWorker(db, registry=registry, worker_id="w-dl")
    worker.process_next_batch()
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    event.available_at = datetime.utcnow() - timedelta(seconds=1)
    db.add(event)
    db.commit()
    worker.process_next_batch()
    delivery = db.query(ElfisEventDelivery).filter(ElfisEventDelivery.event_id == row.event_id).one()
    assert delivery.status == DeliveryStatus.dead_letter.value
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    assert event.status == EventStatus.dead_letter.value
    # Ne pas supprimer
    assert db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).count() == 1


def test_processed_delivery_not_replayed():
    db = _session()
    registry = EventHandlerRegistry()
    handler = _SuccessHandler()
    registry.register(EventNames.VAULT_DOCUMENT_REUSED, handler)
    bus = DatabaseEventBus(db, registry=registry)
    row = bus.publish(
        DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_REUSED,
            organization_id=1,
            payload={"vault_document_id": "v"},
            idempotency_key="noreplay",
        )
    )
    worker = EventWorker(db, registry=registry, worker_id="w1")
    worker.process_next_batch()
    assert handler.calls == 1
    # Forcer un re-claim impossible : statut processed
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    assert event.status == EventStatus.processed.value
    n = worker.process_next_batch()
    assert n == 0
    assert handler.calls == 1


def test_expired_lock_reclaimed():
    db = _session()
    registry = EventHandlerRegistry()
    handler = _SuccessHandler()
    registry.register(EventNames.DELIVERY_EMAIL_SENT, handler)
    bus = DatabaseEventBus(db, registry=registry)
    row = bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_SENT,
            organization_id=1,
            payload={"business_document_id": "1"},
            idempotency_key="lock-1",
        )
    )
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    event.status = EventStatus.processing.value
    event.locked_by = "dead-worker"
    event.locked_at = datetime.utcnow() - timedelta(hours=1)
    db.add(event)
    db.commit()

    worker = EventWorker(
        db,
        registry=registry,
        worker_id="rescuer",
        lock_timeout_seconds=60,
    )
    assert worker.process_next_batch() == 1
    assert handler.calls == 1
    event = db.query(ElfisEvent).filter(ElfisEvent.event_id == row.event_id).one()
    assert event.status == EventStatus.processed.value


def test_sqlite_second_worker_skips_locked_event():
    db = _session()
    registry = EventHandlerRegistry()
    registry.register(EventNames.DELIVERY_EMAIL_STARTED, _SuccessHandler())
    bus = DatabaseEventBus(db, registry=registry)
    bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_STARTED,
            organization_id=1,
            payload={"business_document_id": "1"},
            idempotency_key="conc-1",
        )
    )
    # Simule un event déjà pris récemment
    event = db.query(ElfisEvent).one()
    event.status = EventStatus.processing.value
    event.locked_by = "worker-1"
    event.locked_at = datetime.utcnow()
    db.add(event)
    db.commit()

    worker2 = EventWorker(db, registry=registry, worker_id="worker-2", lock_timeout_seconds=300)
    assert worker2.process_next_batch() == 0
