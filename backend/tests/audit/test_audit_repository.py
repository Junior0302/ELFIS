"""Tests repository audit."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.audit.audit_filters import AuditEventFilters
from app.audit.audit_models import ElfisAuditEvent
from app.audit.audit_repository import AuditRepository
from app.audit.audit_types import AuditAction, AuditCategory, Severity
from tests.audit.conftest_helpers import make_audit_db, seed_user


def _insert(db, **kwargs):
    defaults = dict(
        action=AuditAction.LOGIN_SUCCESS.value,
        severity=Severity.INFO.value,
        category=AuditCategory.AUTH.value,
        success=True,
    )
    defaults.update(kwargs)
    row = ElfisAuditEvent(**defaults)
    AuditRepository(db).insert_event(row)
    db.commit()
    return row


def test_insert_list_count_find():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    r1 = _insert(db, actor_user_id=user.id, correlation_id="corr-1", action="LOGIN_SUCCESS")
    _insert(db, actor_user_id=user.id, action="LOGOUT", success=True)
    _insert(
        db,
        actor_user_id=user.id,
        action="PERMISSION_DENIED",
        success=False,
        severity=Severity.WARNING.value,
        category=AuditCategory.SECURITY.value,
    )

    repo = AuditRepository(db)
    assert repo.find_by_id(r1.id) is not None
    assert len(repo.find_by_correlation("corr-1")) == 1
    assert len(repo.find_recent(limit=10)) == 3

    filters = AuditEventFilters(action="PERMISSION_DENIED", success=False)
    assert repo.count_events(filters) == 1
    assert repo.list_events(filters)[0].action == "PERMISSION_DENIED"

    filters2 = AuditEventFilters(actor_user_id=user.id, severity="INFO")
    assert repo.count_events(filters2) >= 2

    filters3 = AuditEventFilters(date_from=datetime.utcnow() - timedelta(hours=1))
    assert repo.count_events(filters3) == 3
    db.close()


def test_statistics():
    factory, _ = make_audit_db()
    db = factory()
    _insert(db, action="LOGIN_SUCCESS", success=True)
    _insert(db, action="LOGIN_FAILURE", success=False, category=AuditCategory.AUTH.value)
    stats = AuditRepository(db).statistics(hours=24)
    assert stats["total"] == 2
    assert stats["success"] == 1
    assert stats["failure"] == 1
    assert "AUTH" in stats["by_category"] or "LOGIN_SUCCESS" in stats["by_action"]
    db.close()
