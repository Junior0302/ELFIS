"""Tests modèles / création elfis_audit_events."""

from __future__ import annotations

from app.audit.audit_models import ElfisAuditEvent
from app.audit.audit_types import AuditAction, AuditCategory, Severity
from tests.audit.conftest_helpers import make_audit_db, seed_user


def test_create_audit_event_row():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    row = ElfisAuditEvent(
        action=AuditAction.LOGIN_SUCCESS.value,
        severity=Severity.INFO.value,
        category=AuditCategory.AUTH.value,
        actor_user_id=user.id,
        success=True,
        message="ok",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    assert row.id
    assert row.occurred_at is not None
    assert row.action == "LOGIN_SUCCESS"
    db.close()
