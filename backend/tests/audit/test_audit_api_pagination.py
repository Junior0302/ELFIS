"""Tests pagination / filtres / statistiques enrichies API audit."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.audit_logger import AuditLogger
from app.audit.audit_service import AuditService
from app.audit.audit_types import AuditAction, AuditCategory, Severity
from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context
from app.routers import admin_audit
from tests.audit.conftest_helpers import make_audit_db, seed_user


def _client(factory):
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
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({Permission.SECURITY_AUDIT_READ.value}),
    )
    return TestClient(app)


def _seed_events(db, user_id: int) -> None:
    svc = AuditService(db, isolated_writes=False)
    al = AuditLogger(service=svc)
    al.record_login_success(user_id=user_id, email="a@test.local")
    al.record_login_failure(email="b@test.local", reason="bad")
    al.record_permission_denied(user_id=user_id, permission="system.logs.read")
    al.record_role_assignment(actor_user_id=user_id, target_user_id=user_id, role_code="platform_viewer")
    al.record_system_health_refresh(actor_user_id=user_id)
    # Older event
    svc.record(
        AuditAction.LOGOUT.value,
        category=AuditCategory.AUTH,
        severity=Severity.INFO,
        actor_user_id=user_id,
        occurred_at=datetime.utcnow() - timedelta(days=10),
        commit=True,
    )


def test_pagination_and_desc_sort():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    _seed_events(db, user.id)
    db.close()

    client = _client(factory)
    page1 = client.get("/api/admin/audit/events?limit=2&offset=0")
    assert page1.status_code == 200
    body = page1.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total"] >= 5
    assert len(body["items"]) == 2
    # Desc by occurred_at
    t0 = body["items"][0]["occurred_at"]
    t1 = body["items"][1]["occurred_at"]
    assert t0 >= t1

    page2 = client.get("/api/admin/audit/events?limit=2&offset=2")
    assert page2.status_code == 200
    ids1 = {i["id"] for i in body["items"]}
    ids2 = {i["id"] for i in page2.json()["items"]}
    assert ids1.isdisjoint(ids2)


def test_limit_max_and_invalid_enum():
    factory, _ = make_audit_db()
    client = _client(factory)
    # FastAPI Query le=100
    assert client.get("/api/admin/audit/events?limit=500").status_code == 422
    assert client.get("/api/admin/audit/events?severity=NOPE").status_code == 422


def test_filters_category_severity_action_success():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    _seed_events(db, user.id)
    db.close()
    client = _client(factory)

    res = client.get("/api/admin/audit/events?category=AUTH&success=false")
    assert res.status_code == 200
    assert all(i["category"] == "AUTH" and i["success"] is False for i in res.json()["items"])

    res2 = client.get("/api/admin/audit/events?action=PERMISSION_DENIED")
    assert res2.status_code == 200
    assert res2.json()["total"] >= 1
    assert all(i["action"] == "PERMISSION_DENIED" for i in res2.json()["items"])

    res3 = client.get("/api/admin/audit/events?severity=WARNING")
    assert res3.status_code == 200


def test_filters_hours_excludes_old():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    _seed_events(db, user.id)
    db.close()
    client = _client(factory)
    recent = client.get("/api/admin/audit/events?hours=24&limit=100")
    assert recent.status_code == 200
    actions = {i["action"] for i in recent.json()["items"]}
    assert "LOGOUT" not in actions  # 10 days old


def test_statistics_enriched():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    _seed_events(db, user.id)
    db.close()
    client = _client(factory)
    stats = client.get("/api/admin/audit/statistics?hours=24").json()
    assert stats["total"] >= 4
    assert stats["login_failure"] >= 1
    assert stats["permission_denied"] >= 1
    assert stats["iam_changes"] >= 1
    assert "warnings_errors" in stats
    assert stats["hours"] == 24


def test_404_safe_and_metadata_sanitized():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    ev = svc.record(
        "LOGIN_SUCCESS",
        actor_user_id=user.id,
        metadata={"password": "x", "note": "ok"},
        commit=True,
    )
    event_id = ev.id if ev else None
    assert event_id
    db.close()
    client = _client(factory)
    one = client.get(f"/api/admin/audit/events/{event_id}")
    assert one.status_code == 200
    meta = one.json().get("metadata") or {}
    assert "password" not in meta
    assert meta.get("note") == "ok"
    assert "ip_address" in one.json()
    missing = client.get("/api/admin/audit/events/not-found-id-xxxx")
    assert missing.status_code == 404
    assert "traceback" not in missing.text.lower()
