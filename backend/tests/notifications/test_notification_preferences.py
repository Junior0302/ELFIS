"""Tests préférences notifications."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.models_saas import Organization, User
from app.notifications import notification_models  # noqa: F401
from app.notifications.notification_service import NotificationService
from app.notifications.notification_types import NotificationTypes


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Organization(id=1, name="Org", email="o@example.com"))
    db.add(User(id=1, first_name="A", last_name="B", email="a@example.com", status="active"))
    db.commit()
    return db


def test_default_and_update_preferences():
    db = _session()
    svc = NotificationService(db)
    assert svc.get_preferences(organization_id=1, user_id=1) == []
    pref = svc.update_preferences(
        organization_id=1,
        user_id=1,
        notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
        in_app_enabled=True,
        email_enabled=False,
        digest_mode="immediate",
    )
    assert pref["email_enabled"] is False
    prefs = svc.get_preferences(organization_id=1, user_id=1)
    assert len(prefs) == 1
    assert prefs[0]["notification_type"] == NotificationTypes.DELIVERY_EMAIL_SENT
