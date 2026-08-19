"""Tests PermissionResolver — mapping de compatibilité."""

from __future__ import annotations

from types import SimpleNamespace

from app.iam.permission_catalog import Permission, all_permissions
from app.iam.permission_resolver import PermissionResolver
from app.iam.role_permission_map import PLATFORM_ADMIN_PERMISSIONS


def _user(uid: int = 1, status: str = "active"):
    return SimpleNamespace(id=uid, status=status, email="u@test.local", is_platform_admin=False)


def test_platform_admin_keeps_system_health():
    resolver = PermissionResolver()
    ctx = resolver.resolve(user=_user(), is_platform_admin=True)
    assert ctx.is_authenticated
    assert ctx.is_platform_admin
    assert ctx.platform_role == "platform_admin"
    assert Permission.SYSTEM_HEALTH_READ.value in ctx.permissions
    assert Permission.SYSTEM_METRICS_READ.value in ctx.permissions
    assert Permission.SYSTEM_ALERTS_READ.value in ctx.permissions
    assert Permission.SYSTEM_LOGS_READ.value in ctx.permissions
    # Pas toutes les permissions
    assert Permission.BILLING_REFUND.value not in ctx.permissions
    assert Permission.VAULT_SECRETS_MANAGE.value not in ctx.permissions
    assert ctx.permissions == PLATFORM_ADMIN_PERMISSIONS


def test_ordinary_user_no_admin_perms():
    resolver = PermissionResolver()
    ctx = resolver.resolve(user=_user(), is_platform_admin=False)
    assert ctx.is_authenticated
    assert not ctx.is_platform_admin
    assert Permission.SYSTEM_HEALTH_READ.value not in ctx.permissions
    assert Permission.PLATFORM_DASHBOARD_READ.value not in ctx.permissions


def test_org_admin_no_platform_perms():
    resolver = PermissionResolver()
    ctx = resolver.resolve(
        user=_user(),
        is_platform_admin=False,
        organization_id=5,
        organization_role_name="owner",
    )
    assert ctx.organization_role == "organization_admin"
    assert Permission.ORGANIZATIONS_MEMBERS_MANAGE.value in ctx.permissions
    assert Permission.SYSTEM_HEALTH_READ.value not in ctx.permissions
    assert Permission.PLATFORM_SETTINGS_MANAGE.value not in ctx.permissions


def test_super_admin_gets_all_known():
    resolver = PermissionResolver()
    ctx = resolver.resolve(
        user=_user(),
        is_platform_admin=True,
        force_platform_role="super_admin",
    )
    assert ctx.is_super_admin
    assert ctx.permissions == all_permissions()
    assert Permission.BILLING_REFUND.value in ctx.permissions
    assert Permission.VAULT_SECRETS_MANAGE.value in ctx.permissions


def test_unknown_org_role_gets_nothing_extra():
    resolver = PermissionResolver()
    ctx = resolver.resolve(
        user=_user(),
        organization_role_name="wizard_inconnu",
    )
    assert ctx.organization_role == "none"
    assert ctx.permissions == frozenset()


def test_anonymous():
    resolver = PermissionResolver()
    ctx = resolver.resolve(user=None)
    assert not ctx.is_authenticated
    assert ctx.permissions == frozenset()


def test_inactive_user():
    resolver = PermissionResolver()
    ctx = resolver.resolve(user=_user(status="suspended"), is_platform_admin=True)
    assert not ctx.is_authenticated
