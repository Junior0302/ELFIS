"""Tests modèles / contraintes IAM."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.iam.iam_models import ElfisPlatformRole
from app.iam.system_roles import bootstrap_system_roles
from tests.iam.conftest_helpers import make_iam_db, seed_user


def test_unique_role_code():
    factory, _ = make_iam_db()
    db = factory()
    db.add(ElfisPlatformRole(code="r1", name="R1", is_system=False))
    db.commit()
    db.add(ElfisPlatformRole(code="r1", name="R1bis", is_system=False))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_bootstrap_creates_system_roles_idempotent():
    factory, _ = make_iam_db()
    db = factory()
    a = bootstrap_system_roles(db, commit=True)
    b = bootstrap_system_roles(db, commit=True)
    assert a["roles_created"] >= 5
    assert b["roles_created"] == 0
    assert a["user_assignments"] == 0
    codes = {r.code for r in db.query(ElfisPlatformRole).all()}
    assert {"super_admin", "platform_admin", "platform_operator", "platform_support", "platform_viewer"} <= codes
    db.close()


def test_inactive_and_expired_assignment_ignored():
    from datetime import datetime, timedelta

    from app.iam.platform_role_service import PlatformRoleService

    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    svc = PlatformRoleService(db)
    svc.assign_role_to_user(user.id, "platform_viewer")
    assert "system.health.read" in svc.effective_permissions_for_user(user.id)

    # expire
    role = svc.get_role_by_code("platform_viewer")
    assignment = svc.user_roles.get_assignment(user.id, role.id)
    assignment.assigned_at = datetime.utcnow() - timedelta(hours=2)
    assignment.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.add(assignment)
    db.commit()

    from app.iam.permission_cache import effective_permissions_cache

    effective_permissions_cache.clear()
    assert "system.health.read" not in svc.effective_permissions_for_user(user.id)

    # inactive
    assignment.is_active = False
    assignment.expires_at = None
    db.add(assignment)
    db.commit()
    effective_permissions_cache.clear()
    assert svc.effective_permissions_for_user(user.id) == frozenset()
    db.close()
