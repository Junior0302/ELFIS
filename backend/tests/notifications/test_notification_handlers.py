"""Tests handlers Event Bus → notifications."""

from __future__ import annotations

import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_context import EventContext
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_saas import Organization, User
from app.notifications import notification_models  # noqa: F401
from app.notifications.notification_handlers import (
    DeliveryEmailFailedNotificationHandler,
    DeliveryEmailSentNotificationHandler,
    DocumentArchivedNotificationHandler,
)
from app.notifications.notification_models import ElfisNotification


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    db.add(Organization(id=1, name="Org", email="o@example.com"))
    db.add(User(id=7, first_name="A", last_name="B", email="a@example.com", status="active"))
    db.commit()


def test_email_sent_handler_creates_success_notification():
    db = _session()
    _seed(db)
    event = DomainEvent(
        event_name=EventNames.DELIVERY_EMAIL_SENT,
        organization_id=1,
        payload={
            "business_document_type": "invoice",
            "document_number": "FACT-9",
            "business_document_id": "9",
            "vault_document_id": "v9",
        },
        metadata={"actor_user_id": "7", "source": "document_delivery"},
    )
    DeliveryEmailSentNotificationHandler().handle(
        event, EventContext(db=db, worker_id="t", attempt_count=1)
    )
    row = db.query(ElfisNotification).one()
    assert row.severity == "success"
    assert row.user_id == 7
    # idempotent
    DeliveryEmailSentNotificationHandler().handle(
        event, EventContext(db=db, worker_id="t", attempt_count=2)
    )
    assert db.query(ElfisNotification).count() == 1


def test_email_failed_handler_creates_error():
    db = _session()
    _seed(db)
    event = DomainEvent(
        event_name=EventNames.DELIVERY_EMAIL_FAILED,
        organization_id=1,
        payload={"business_document_id": "3", "document_number": "FACT-3"},
        metadata={"actor_user_id": "7"},
    )
    DeliveryEmailFailedNotificationHandler().handle(
        event, EventContext(db=db, worker_id="t", attempt_count=1)
    )
    row = db.query(ElfisNotification).one()
    assert row.severity == "error"
    assert "archivé" in row.message.lower() or "archive" in row.message.lower()


def test_archived_without_notify_user_skips():
    db = _session()
    _seed(db)
    event = DomainEvent(
        event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
        organization_id=1,
        payload={"vault_document_id": "v1", "archive_status": "archived"},
        metadata={"actor_user_id": "7"},
    )
    DocumentArchivedNotificationHandler().handle(
        event, EventContext(db=db, worker_id="t", attempt_count=1)
    )
    assert db.query(ElfisNotification).count() == 0


def test_archived_with_notify_user_creates():
    db = _session()
    _seed(db)
    event = DomainEvent(
        event_id=uuid.uuid4(),
        event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
        organization_id=1,
        payload={"vault_document_id": "v2", "document_number": "D-1"},
        metadata={"actor_user_id": "7", "notify_user": True},
    )
    DocumentArchivedNotificationHandler().handle(
        event, EventContext(db=db, worker_id="t", attempt_count=1)
    )
    assert db.query(ElfisNotification).count() == 1
