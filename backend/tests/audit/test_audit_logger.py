"""Tests AuditLogger helpers."""

from __future__ import annotations

from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_logger import AuditLogger
from app.audit.audit_service import AuditService
from app.audit.audit_types import AuditAction
from tests.audit.conftest_helpers import make_audit_db, seed_user


def test_logger_helpers():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    al = AuditLogger(service=svc)

    assert al.record_login_success(user_id=user.id, email=user.email) is not None
    assert al.record_login_failure(email="x@y.z", reason="bad_token") is not None
    assert al.record_logout(user_id=user.id) is not None
    assert al.record_role_assignment(target_user_id=user.id, role_code="platform_viewer") is not None
    assert al.record_role_removal(target_user_id=user.id, role_code="platform_viewer") is not None
    assert al.record_permission_denied(user_id=user.id, permission="x.y") is not None
    assert al.record_system_health_refresh(actor_user_id=user.id) is not None
    assert al.record_job_retry(job_id="j1") is not None
    assert al.record_event_retry(event_id="e1") is not None
    assert al.record_subscription_created(subscription_id="s1") is not None
    assert al.record_invoice_import(document_id="d1") is not None

    actions = {e.action for e in svc.list_events(AuditEventFilters(limit=50))}
    assert AuditAction.LOGIN_SUCCESS.value in actions
    assert AuditAction.PERMISSION_DENIED.value in actions
    assert AuditAction.HEALTH_REFRESH.value in actions
    db.close()
