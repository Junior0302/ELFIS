"""Tests API admin audit (lecture seule)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.audit_logger import AuditLogger
from app.audit.audit_service import AuditService
from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context
from app.routers import admin_audit
from tests.audit.conftest_helpers import make_audit_db, seed_user


def _client_with_db(factory):
    from app.database import get_db

    app = FastAPI()
    app.include_router(admin_audit.router, prefix="/api")

    def _db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    return app


def test_unauthenticated_401():
    factory, _ = make_audit_db()
    app = _client_with_db(factory)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        is_authenticated=False
    )
    client = TestClient(app)
    assert client.get("/api/admin/audit/events").status_code == 401


def test_forbidden_403():
    factory, _ = make_audit_db()
    app = _client_with_db(factory)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({"system.health.read"}),
    )
    client = TestClient(app)
    assert client.get("/api/admin/audit/events").status_code == 403


def test_reader_200_no_secrets():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    AuditLogger(service=svc).record_login_success(
        user_id=user.id,
        email=user.email,
        metadata={"note": "ok", "password": "nope"},
    )
    db.close()

    app = _client_with_db(factory)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({Permission.SECURITY_AUDIT_READ.value}),
    )
    client = TestClient(app)
    res = client.get("/api/admin/audit/events")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert "limit" in body and "offset" in body
    assert "password" not in res.text.lower() or "***" in res.text
    assert "jwt" not in res.text.lower()
    event_id = body["items"][0]["id"]

    one = client.get(f"/api/admin/audit/events/{event_id}")
    assert one.status_code == 200
    assert one.json()["action"] == "LOGIN_SUCCESS"

    stats = client.get("/api/admin/audit/statistics?hours=24")
    assert stats.status_code == 200
    assert stats.json()["total"] >= 1

    missing = client.get("/api/admin/audit/events/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
