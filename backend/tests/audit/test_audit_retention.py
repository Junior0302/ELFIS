"""Tests rétention / archivage audit."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.audit.audit_models import ElfisAuditEvent, ElfisAuditEventArchive
from app.audit.audit_retention import AuditRetentionService
from app.audit.audit_service import AuditService
from app.audit.audit_types import AuditCategory, Severity
from tests.audit.conftest_helpers import make_audit_db, seed_user


def test_critical_kept_longer_than_info():
    factory, _ = make_audit_db()
    db = factory()
    svc = AuditRetentionService(db)
    info = ElfisAuditEvent(
        action="X",
        category=AuditCategory.OTHER.value,
        severity=Severity.INFO.value,
        occurred_at=datetime.utcnow(),
    )
    crit = ElfisAuditEvent(
        action="Y",
        category=AuditCategory.OTHER.value,
        severity=Severity.CRITICAL.value,
        occurred_at=datetime.utcnow(),
    )
    assert svc.retention_days_for(crit) > svc.retention_days_for(info)
    assert svc.calculate_expiration(crit) > svc.calculate_expiration(info)
    db.close()


def test_preview_no_write_and_archive_confirm():
    factory, _ = make_audit_db()
    db = factory()
    user = seed_user(db)
    write = AuditService(db, isolated_writes=False)
    old = datetime.utcnow() - timedelta(days=800)
    write.record(
        "LOGIN_SUCCESS",
        category=AuditCategory.AUTH,
        severity=Severity.INFO,
        actor_user_id=user.id,
        occurred_at=old,
        commit=True,
    )
    write.record(
        "PERMISSION_DENIED",
        category=AuditCategory.SECURITY,
        severity=Severity.CRITICAL,
        actor_user_id=user.id,
        occurred_at=old,
        commit=True,
    )

    retention = AuditRetentionService(db)
    preview = retention.preview_retention()
    assert preview["expired_count"] >= 1
    assert db.query(ElfisAuditEvent).count() >= 2

    with pytest.raises(ValueError, match="confirmation_required"):
        retention.archive_expired(confirm=False)

    result = retention.archive_expired(confirm=True, batch_size=100)
    assert result["archived"] >= 1
    assert db.query(ElfisAuditEventArchive).count() >= 1

    # Idempotent second pass
    result2 = retention.archive_expired(confirm=True, batch_size=100)
    assert result2["errors"] == 0
    db.close()
