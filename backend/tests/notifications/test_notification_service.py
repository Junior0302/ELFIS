"""Tests NotificationService."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models_saas import Organization, User
from app.notifications import notification_models  # noqa: F401
from app.notifications.notification_exceptions import NotificationValidationError
from app.notifications.notification_models import ElfisNotification, ElfisNotificationDelivery
from app.notifications.notification_renderer import validate_action_url
from app.notifications.notification_schemas import NotificationRequest
from app.notifications.notification_service import NotificationService
from app.notifications.notification_types import (
    DeliveryStatus,
    NotificationChannel,
    NotificationStatus,
    NotificationTypes,
    TEMPLATE_DOCUMENT_EMAIL_FAILED,
    TEMPLATE_DOCUMENT_EMAIL_SENT,
    TEMPLATE_SYSTEM_GENERIC,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    db.add(Organization(id=1, name="Org A", email="a@example.com"))
    db.add(Organization(id=2, name="Org B", email="b@example.com"))
    db.add(User(id=1, first_name="A", last_name="One", email="u1@example.com", status="active"))
    db.add(User(id=2, first_name="B", last_name="Two", email="u2@example.com", status="active"))
    db.commit()


def test_create_in_app_persisted_with_sent_delivery():
    db = _session()
    _seed(db)
    result = NotificationService(db).create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"business_document_type": "invoice", "document_number": "FACT-1"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="n1",
        )
    )
    assert result.created is True
    row = db.query(ElfisNotification).filter(ElfisNotification.notification_id == result.notification_id).one()
    assert row.status == NotificationStatus.UNREAD
    assert "FACT-1" in row.message
    delivery = db.query(ElfisNotificationDelivery).one()
    assert delivery.channel == NotificationChannel.IN_APP
    assert delivery.status == DeliveryStatus.SENT
    assert db.query(ElfisEvent).filter(ElfisEvent.event_name == EventNames.NOTIFICATION_CREATED).count() == 1


def test_idempotency_prevents_duplicate():
    db = _session()
    _seed(db)
    svc = NotificationService(db)
    req = NotificationRequest(
        organization_id=1,
        user_id=1,
        notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
        category="email",
        template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
        template_data={"document_number": "X"},
        channels=[NotificationChannel.IN_APP],
        idempotency_key="same",
    )
    a = svc.create_notification(req)
    b = svc.create_notification(req)
    assert a.notification_id == b.notification_id
    assert b.created is False
    assert db.query(ElfisNotification).count() == 1


def test_preferences_disable_in_app():
    db = _session()
    _seed(db)
    svc = NotificationService(db)
    svc.update_preferences(
        organization_id=1,
        user_id=1,
        notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
        in_app_enabled=False,
        email_enabled=False,
    )
    with pytest.raises(NotificationValidationError):
        svc.create_notification(
            NotificationRequest(
                organization_id=1,
                user_id=1,
                notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
                category="email",
                template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
                template_data={"document_number": "Y"},
                channels=[NotificationChannel.IN_APP],
            )
        )


@patch("app.notifications.notification_email_sender.send_email")
def test_system_email_channel(mock_send):
    from app.services.mailer import SendEmailResult

    mock_send.return_value = SendEmailResult(provider="brevo", provider_message_id="m1")
    db = _session()
    _seed(db)
    with patch("app.notifications.notification_email_sender.email_configured", return_value=True):
        result = NotificationService(db).create_notification(
            NotificationRequest(
                organization_id=1,
                user_id=1,
                notification_type=NotificationTypes.SYSTEM_WELCOME,
                category="system",
                template_name=TEMPLATE_SYSTEM_GENERIC,
                template_data={"title": "Bienvenue", "message": "Hello"},
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                email_recipient="u1@example.com",
                idempotency_key="sys1",
            )
        )
    assert any(d.channel == "email" and d.status == "sent" for d in result.deliveries)
    mock_send.assert_called_once()


def test_list_isolation_and_org_wide():
    db = _session()
    _seed(db)
    svc = NotificationService(db)
    svc.create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"document_number": "U1"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="u1",
        )
    )
    svc.create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=None,
            notification_type=NotificationTypes.DELIVERY_EMAIL_FAILED,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_FAILED,
            template_data={"document_number": "ORG"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="org",
        )
    )
    svc.create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=2,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"document_number": "U2"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="u2",
        )
    )
    items, total = svc.list_notifications(organization_id=1, user_id=1)
    assert total == 2
    nums = " ".join(i.message for i in items)
    assert "U2" not in nums
    assert "ORG" in nums or "U1" in nums


def test_cross_tenant_get_404():
    db = _session()
    _seed(db)
    svc = NotificationService(db)
    result = svc.create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"document_number": "Z"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="z",
        )
    )
    from app.notifications.notification_exceptions import NotificationNotFoundError

    with pytest.raises(NotificationNotFoundError):
        svc.get_notification(
            organization_id=2, user_id=1, notification_id=result.notification_id
        )


def test_unread_mark_read_archive_expired():
    db = _session()
    _seed(db)
    svc = NotificationService(db)
    r = svc.create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"document_number": "R"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="r1",
        )
    )
    assert svc.get_unread_count(organization_id=1, user_id=1) == 1
    svc.mark_as_read(organization_id=1, user_id=1, notification_id=r.notification_id)
    assert svc.get_unread_count(organization_id=1, user_id=1) == 0
    assert db.query(ElfisEvent).filter(ElfisEvent.event_name == EventNames.NOTIFICATION_READ).count() == 1
    svc.archive_notification(organization_id=1, user_id=1, notification_id=r.notification_id)

    expired = svc.create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_FAILED,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_FAILED,
            template_data={"document_number": "E"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="exp",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
    )
    assert svc.get_unread_count(organization_id=1, user_id=1) == 0
    assert expired.notification_id


def test_dangerous_action_url():
    with pytest.raises(NotificationValidationError):
        validate_action_url("javascript:alert(1)")
    with pytest.raises(NotificationValidationError):
        validate_action_url("https://evil.example")
    assert validate_action_url("/documents") == "/documents"
