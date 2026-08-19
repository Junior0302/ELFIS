"""Tests AuditService — y compris non-blocage métier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_sanitize import assert_no_secrets_in_payload
from app.audit.audit_service import AuditService
from app.audit.audit_types import AuditAction, AuditCategory, Severity
from tests.audit.conftest_helpers import make_audit_db, seed_user


def test_record_and_list():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    svc = AuditService(db, isolated_writes=False)
    ev = svc.record(
        AuditAction.LOGIN_SUCCESS.value,
        actor_user_id=user.id,
        actor_email=user.email,
        category=AuditCategory.AUTH,
        severity=Severity.INFO,
        metadata={"password": "secret", "note": "ok"},
        commit=True,
    )
    assert ev is not None
    assert ev.metadata_json is None or "password" not in (ev.metadata_json or {})
    assert "note" in (ev.metadata_json or {})
    assert assert_no_secrets_in_payload({"m": ev.metadata_json, "msg": ev.message})

    items = svc.list_events(AuditEventFilters(actor_user_id=user.id))
    assert len(items) == 1
    db.close()


def test_record_continues_on_db_error():
    factory, _ = make_audit_db()
    db = factory()
    svc = AuditService(db, isolated_writes=False)

    with patch.object(svc, "_persist_shared", side_effect=RuntimeError("db down")):
        result = svc.record("LOGIN_SUCCESS", commit=True)
    assert result is None
    # session toujours utilisable
    user = seed_user(db)
    assert user.id is not None
    db.close()


def test_log_alias():
    factory, _ = make_audit_db()
    db = factory()
    svc = AuditService(db, isolated_writes=False)
    assert svc.log("HEALTH_REFRESH", category=AuditCategory.SYSTEM, commit=True) is not None
    db.close()
