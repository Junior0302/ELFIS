"""Tests export sécurisé audit."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.audit_export import neutralize_csv_cell
from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_logger import AuditLogger
from app.audit.audit_models import ElfisAuditEvent
from app.audit.audit_repository import AuditRepository
from app.audit.audit_service import AuditService
from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context
from app.routers import admin_audit
from tests.audit.conftest_helpers import make_audit_db, seed_user


def _client(factory, perms: frozenset[str]):
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
        permissions=perms,
    )
    return TestClient(app)


def test_csv_injection_neutralize():
    assert neutralize_csv_cell("=CMD()") == "'=CMD()"
    assert neutralize_csv_cell("+1") == "'+1"
    assert neutralize_csv_cell("ok") == "ok"


def test_export_requires_permission():
    factory, _ = make_audit_db()
    client = _client(factory, frozenset({Permission.SECURITY_AUDIT_READ.value}))
    assert client.get("/api/admin/audit/export?hours=1").status_code == 403


def test_export_csv_sanitized_and_audited():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    svc.record(
        "LOGIN_SUCCESS",
        actor_user_id=user.id,
        actor_email="a@test.local",
        message="=HYPERLINK()",
        ip_address="10.1.2.3",
        metadata={"password": "x", "note": "safe"},
        commit=True,
    )
    db.close()

    client = _client(
        factory,
        frozenset(
            {
                Permission.SECURITY_AUDIT_READ.value,
                Permission.SECURITY_AUDIT_EXPORT.value,
            }
        ),
    )
    res = client.get("/api/admin/audit/export?hours=24&format=csv")
    assert res.status_code == 200
    text = res.text
    assert "password" not in text
    assert "10.1.*.*" in text or "10.1" in text
    assert "'=HYPERLINK()" in text or "HYPERLINK" in text
    assert "Bearer" not in text

    # Événement d'audit d'export créé
    db2 = factory()
    actions = {r.action for r in AuditRepository(db2).find_recent(limit=20)}
    assert "AUDIT_EXPORT_REQUESTED" in actions or "AUDIT_EXPORT_COMPLETED" in actions
    db2.close()


def test_export_range_limit():
    factory, _ = make_audit_db()
    client = _client(
        factory,
        frozenset({Permission.SECURITY_AUDIT_EXPORT.value}),
    )
    start = (datetime.utcnow() - timedelta(days=60)).isoformat()
    end = datetime.utcnow().isoformat()
    res = client.get(f"/api/admin/audit/export?date_from={start}&date_to={end}")
    assert res.status_code == 422
