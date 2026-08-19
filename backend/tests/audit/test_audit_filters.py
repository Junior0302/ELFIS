"""Tests filtres audit."""

from __future__ import annotations

from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_logger import AuditLogger
from app.audit.audit_service import AuditService
from tests.audit.conftest_helpers import make_audit_db


def test_filters_normalize_and_cap():
    f = AuditEventFilters(severity="info", category="auth", action="login_success", limit=9999, offset=-1)
    assert f.severity == "INFO"
    assert f.category == "AUTH"
    assert f.action == "LOGIN_SUCCESS"
    assert f.limit == 100
    assert f.offset == 0


def test_filter_by_service_product():
    factory, _ = make_audit_db()
    db = factory()
    from tests.audit.conftest_helpers import seed_user

    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    al = AuditLogger(service=svc)
    al.record_login_success(user_id=user.id)
    al.record_system_health_refresh(actor_user_id=user.id)

    auth_only = svc.list_events(AuditEventFilters(service="auth"))
    assert all(e.service == "auth" for e in auth_only)
    assert len(auth_only) == 1

    health = svc.list_events(AuditEventFilters(service="system_health", product="elfis-core"))
    assert len(health) == 1
    db.close()
