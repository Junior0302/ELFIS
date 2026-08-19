"""Tests recherche avancée audit."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.audit_logger import AuditLogger
from app.audit.audit_service import AuditService
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


def test_free_text_and_target_filters():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    AuditLogger(service=svc).record_role_assignment(
        actor_user_id=user.id,
        target_user_id=user.id,
        role_code="platform_viewer",
    )
    svc.record(
        "LOGIN_SUCCESS",
        actor_user_id=user.id,
        actor_email="findme@test.local",
        message="hello searchable",
        target_type="user",
        target_id=str(user.id),
        commit=True,
    )
    db.close()
    client = _client(factory)

    res = client.get("/api/admin/audit/events?q=findme")
    assert res.status_code == 200
    assert res.json()["total"] >= 1

    res2 = client.get("/api/admin/audit/events?target_type=user&q=searchable")
    assert res2.status_code == 200
    assert all(i["target_type"] == "user" for i in res2.json()["items"])


def test_date_range_too_large():
    factory, _ = make_audit_db()
    client = _client(factory)
    start = (datetime.utcnow() - timedelta(days=400)).isoformat()
    end = datetime.utcnow().isoformat()
    res = client.get(f"/api/admin/audit/events?date_from={start}&date_to={end}")
    assert res.status_code == 422


def test_sort_stable():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    for i in range(3):
        svc.record("LOGIN_SUCCESS", actor_user_id=user.id, message=f"n{i}", commit=True)
    db.close()
    client = _client(factory)
    desc = client.get("/api/admin/audit/events?sort=occurred_at_desc&limit=10").json()["items"]
    asc = client.get("/api/admin/audit/events?sort=occurred_at_asc&limit=10").json()["items"]
    assert desc[0]["occurred_at"] >= desc[-1]["occurred_at"]
    assert asc[0]["occurred_at"] <= asc[-1]["occurred_at"]
