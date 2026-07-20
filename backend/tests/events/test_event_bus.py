"""Tests Event Bus — publication et registry."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_bus import DatabaseEventBus
from app.events.event_context import EventContext, sanitize_error_message
from app.events.event_models import ElfisEvent, ElfisEventDelivery
from app.events.event_registry import EventHandler, EventHandlerRegistry
from app.events.event_schemas import DomainEvent, EventStatus
from app.events.event_types import EventNames
from app.events.exceptions import EventDuplicateError, EventValidationError


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class _OkHandler(EventHandler):
    handler_name = "ok_handler_v1"

    def __init__(self):
        self.calls = 0

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        self.calls += 1


class _OtherHandler(EventHandler):
    handler_name = "other_handler_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        return None


def test_publish_persists_event_and_payload():
    db = _session()
    registry = EventHandlerRegistry()
    registry.register(EventNames.VAULT_DOCUMENT_ARCHIVED, _OkHandler())
    bus = DatabaseEventBus(db, registry=registry)
    correlation = uuid.uuid4()
    causation = uuid.uuid4()
    event = DomainEvent(
        event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
        organization_id=1,
        aggregate_type="vault_document",
        aggregate_id="doc-1",
        payload={
            "vault_document_id": "doc-1",
            "business_document_id": "42",
            "business_document_type": "invoice",
            "document_type": "customer_invoice",
            "archive_status": "archived",
            "reused_existing_archive": False,
        },
        metadata={"source": "document_delivery", "actor_user_id": "7", "request_id": None},
        idempotency_key="pub-1",
        correlation_id=correlation,
        causation_id=causation,
    )
    row = bus.publish(event)
    assert row.event_id == str(event.event_id)
    assert row.status == EventStatus.pending.value
    assert row.payload["vault_document_id"] == "doc-1"
    assert isinstance(row.payload, dict)
    assert row.correlation_id == str(correlation)
    assert row.causation_id == str(causation)
    assert "pdf" not in row.payload
    assert db.query(ElfisEvent).count() == 1


def test_idempotency_key_prevents_duplicate():
    db = _session()
    bus = DatabaseEventBus(db, registry=EventHandlerRegistry())
    e1 = DomainEvent(
        event_name=EventNames.DELIVERY_EMAIL_SENT,
        organization_id=1,
        payload={"business_document_id": "1"},
        idempotency_key="same-key",
    )
    first = bus.publish(e1)
    e2 = DomainEvent(
        event_name=EventNames.DELIVERY_EMAIL_SENT,
        organization_id=1,
        payload={"business_document_id": "1"},
        idempotency_key="same-key",
    )
    second = bus.publish(e2)
    assert second.event_id == first.event_id
    assert db.query(ElfisEvent).count() == 1


def test_two_different_events_accepted():
    db = _session()
    bus = DatabaseEventBus(db, registry=EventHandlerRegistry())
    bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_STARTED,
            organization_id=1,
            payload={"business_document_id": "1"},
            idempotency_key="a",
        )
    )
    bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_SENT,
            organization_id=1,
            payload={"business_document_id": "1"},
            idempotency_key="b",
        )
    )
    assert db.query(ElfisEvent).count() == 2


def test_handlers_registered_and_deliveries_created():
    db = _session()
    registry = EventHandlerRegistry()
    h1 = _OkHandler()
    h2 = _OtherHandler()
    registry.register(EventNames.VAULT_DOCUMENT_ARCHIVED, h1)
    registry.register(EventNames.VAULT_DOCUMENT_ARCHIVED, h2)
    bus = DatabaseEventBus(db, registry=registry)
    assert len(bus.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)) == 2
    row = bus.publish(
        DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
            organization_id=3,
            payload={"vault_document_id": "v1", "archive_status": "archived"},
            idempotency_key="deliv-1",
        )
    )
    deliveries = db.query(ElfisEventDelivery).filter(ElfisEventDelivery.event_id == row.event_id).all()
    assert len(deliveries) == 2
    names = {d.handler_name for d in deliveries}
    assert names == {"ok_handler_v1", "other_handler_v1"}


def test_forbidden_payload_rejected():
    with pytest.raises(Exception):
        DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
            organization_id=1,
            payload={"pdf_bytes": "xxx"},
        )


def test_org_isolation_on_list():
    db = _session()
    bus = DatabaseEventBus(db, registry=EventHandlerRegistry())
    bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_SENT,
            organization_id=1,
            payload={"x": 1},
            idempotency_key="o1",
        )
    )
    bus.publish(
        DomainEvent(
            event_name=EventNames.DELIVERY_EMAIL_SENT,
            organization_id=2,
            payload={"x": 2},
            idempotency_key="o2",
        )
    )
    from app.events.event_repository import EventRepository

    rows, total = EventRepository(db).list_events(organization_id=1)
    assert total == 1
    assert rows[0].organization_id == 1


def test_sanitize_error_strips_secrets():
    msg = sanitize_error_message("boom xkeysib-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789token")
    assert "xkeysib-" not in msg.lower() or "[REDACTED]" in msg
    assert "PDF" not in sanitize_error_message("%PDF-1.4 secret") or "[REDACTED]" in sanitize_error_message(
        "%PDF-1.4 secret"
    )
