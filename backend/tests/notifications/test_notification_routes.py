"""Tests routes notifications + platform."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.events import event_models  # noqa: F401
from app.models_saas import Organization, User
from app.notifications import notification_models  # noqa: F401
from app.notifications.notification_schemas import NotificationRequest
from app.notifications.notification_service import NotificationService
from app.notifications.notification_types import (
    NotificationChannel,
    NotificationTypes,
    TEMPLATE_DOCUMENT_EMAIL_SENT,
)
from app.routers import notifications as notifications_router
from app.routers import platform as platform_router


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _make_client(*, platform: bool = False):
    engine = _engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Org", email="o@example.com"))
    db.add(
        User(
            id=1,
            first_name="A",
            last_name="B",
            email="a@example.com",
            status="active",
            is_platform_admin=platform,
        )
    )
    db.commit()

    app = FastAPI()
    app.include_router(notifications_router.router, prefix="/api")
    app.include_router(platform_router.router, prefix="/api")

    def override_db():
        try:
            yield db
        finally:
            pass

    user = db.get(User, 1)

    def override_auth():
        return AuthContext(
            user=user,
            organization_id=1,
            role="owner",
            permissions=["*"],
        )

    def override_sub():
        return None

    def override_platform():
        if not platform:
            from fastapi import HTTPException

            raise HTTPException(403, detail="platform_admin_required")
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_context] = override_auth
    app.dependency_overrides[require_active_subscription] = override_sub
    app.dependency_overrides[require_platform_admin] = override_platform
    return TestClient(app), db


def test_user_routes_list_unread_read():
    client, db = _make_client()
    created = NotificationService(db).create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"document_number": "F-1"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="route-1",
        )
    )
    unread = client.get("/api/notifications/unread-count")
    assert unread.status_code == 200
    assert unread.json()["count"] == 1
    listed = client.get("/api/notifications")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    marked = client.post(f"/api/notifications/{created.notification_id}/read")
    assert marked.status_code == 200
    assert client.get("/api/notifications/unread-count").json()["count"] == 0
    missing = client.post("/api/notifications/does-not-exist/read")
    assert missing.status_code == 404


def test_platform_allowed_and_denied():
    denied, _ = _make_client(platform=False)
    assert denied.get("/api/platform/notifications").status_code == 403

    allowed, db = _make_client(platform=True)
    NotificationService(db).create_notification(
        NotificationRequest(
            organization_id=1,
            user_id=1,
            notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
            category="email",
            template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
            template_data={"document_number": "P-1"},
            channels=[NotificationChannel.IN_APP],
            idempotency_key="plat-1",
        )
    )
    resp = allowed.get("/api/platform/notifications")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert "message" not in resp.json()["notifications"][0]
