"""Tests PlatformRoleService."""

from __future__ import annotations

import pytest

from app.iam.permission_cache import configure_permission_cache, effective_permissions_cache
from app.iam.platform_role_service import PlatformRoleService
from app.iam.system_roles import bootstrap_system_roles
from tests.iam.conftest_helpers import make_iam_db, seed_user


@pytest.fixture(autouse=True)
def _reset_cache():
    configure_permission_cache(ttl_seconds=30.0)
    effective_permissions_cache.clear()
    yield
    effective_permissions_cache.clear()


def test_assign_revoke_and_custom_role():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    svc = PlatformRoleService(db)

    svc.assign_role_to_user(user.id, "platform_operator")
    perms = svc.effective_permissions_for_user(user.id)
    assert "system.health.read" in perms
    assert "jobs.read" in perms
    assert "billing.manage" not in perms

    svc.revoke_role_from_user(user.id, "platform_operator")
    assert svc.effective_permissions_for_user(user.id) == frozenset()

    role = svc.create_custom_role(
        code="custom_ops",
        name="Custom",
        permission_codes=["system.health.read", "system.metrics.read"],
    )
    assert role.is_system is False
    svc.assign_role_to_user(user.id, "custom_ops")
    assert "system.metrics.read" in svc.effective_permissions_for_user(user.id)
    db.close()


def test_system_role_cannot_deactivate():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    svc = PlatformRoleService(db)
    role = svc.get_role_by_code("platform_admin")
    with pytest.raises(ValueError, match="system_role"):
        svc.set_role_active(role.id, is_active=False)
    db.close()


def test_super_admin_gets_all():
    from app.iam.permission_catalog import all_permissions

    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    svc = PlatformRoleService(db)
    svc.assign_role_to_user(user.id, "super_admin")
    assert svc.effective_permissions_for_user(user.id) == all_permissions()
    db.close()
