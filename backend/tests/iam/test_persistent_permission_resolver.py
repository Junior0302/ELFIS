"""Tests resolver hybride avec rôles persistants."""

from __future__ import annotations

from types import SimpleNamespace

from app.iam.permission_catalog import Permission, all_permissions
from app.iam.permission_resolver import PermissionResolver
from app.iam.system_roles import bootstrap_system_roles
from app.iam.platform_role_service import PlatformRoleService
from tests.iam.conftest_helpers import make_iam_db, seed_user


def test_persistent_role_grants_without_is_platform_admin():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db, is_platform_admin=False)
    PlatformRoleService(db).assign_role_to_user(user.id, "platform_viewer")

    ctx = PermissionResolver().resolve(user=user, is_platform_admin=False, db=db)
    assert Permission.SYSTEM_HEALTH_READ.value in ctx.permissions
    assert Permission.SYSTEM_METRICS_READ.value in ctx.permissions
    assert Permission.USERS_DISABLE.value not in ctx.permissions
    assert not ctx.is_platform_admin or ctx.platform_role == "platform_viewer"
    db.close()


def test_compat_platform_admin_preserved():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db, is_platform_admin=True)
    ctx = PermissionResolver().resolve(user=user, is_platform_admin=True, db=db)
    assert Permission.SYSTEM_HEALTH_READ.value in ctx.permissions
    assert Permission.PLATFORM_DASHBOARD_READ.value in ctx.permissions
    db.close()


def test_org_role_no_platform_perms():
    user = SimpleNamespace(id=1, status="active")
    ctx = PermissionResolver().resolve(
        user=user,
        is_platform_admin=False,
        organization_role_name="owner",
        db=None,
    )
    assert Permission.ORGANIZATIONS_MEMBERS_MANAGE.value in ctx.permissions
    assert Permission.SYSTEM_HEALTH_READ.value not in ctx.permissions


def test_persistent_super_admin():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    PlatformRoleService(db).assign_role_to_user(user.id, "super_admin")
    ctx = PermissionResolver().resolve(user=user, is_platform_admin=False, db=db)
    assert ctx.is_super_admin
    assert ctx.permissions == all_permissions()
    db.close()


def test_no_role_denied_platform():
    user = SimpleNamespace(id=99, status="active")
    ctx = PermissionResolver().resolve(user=user, is_platform_admin=False, db=None)
    assert Permission.SYSTEM_HEALTH_READ.value not in ctx.permissions
    assert ctx.platform_role == "none"
