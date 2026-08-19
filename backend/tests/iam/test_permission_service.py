"""Tests PermissionService."""

from __future__ import annotations

import pytest

from app.iam.permission_catalog import Permission, all_permissions
from app.iam.permission_context import PermissionContext
from app.iam.permission_exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    UnknownPermissionError,
)
from app.iam.permission_service import PermissionService


def _ctx(*perms: str, auth: bool = True) -> PermissionContext:
    return PermissionContext(
        user_id=1 if auth else None,
        is_authenticated=auth,
        permissions=frozenset(perms),
    )


def test_has_permission_single():
    svc = PermissionService()
    ctx = _ctx(Permission.SYSTEM_HEALTH_READ.value)
    assert svc.has_permission(ctx, Permission.SYSTEM_HEALTH_READ.value)
    assert not svc.has_permission(ctx, Permission.SYSTEM_LOGS_READ.value)


def test_any_and_all():
    svc = PermissionService()
    ctx = _ctx(Permission.SYSTEM_HEALTH_READ.value, Permission.SYSTEM_METRICS_READ.value)
    assert svc.has_any_permission(
        ctx, [Permission.SYSTEM_LOGS_READ.value, Permission.SYSTEM_HEALTH_READ.value]
    )
    assert svc.has_all_permissions(
        ctx, [Permission.SYSTEM_HEALTH_READ.value, Permission.SYSTEM_METRICS_READ.value]
    )
    assert not svc.has_all_permissions(
        ctx, [Permission.SYSTEM_HEALTH_READ.value, Permission.SYSTEM_LOGS_READ.value]
    )


def test_deny_by_default_anonymous():
    svc = PermissionService()
    ctx = _ctx(auth=False)
    assert not svc.has_permission(ctx, Permission.SYSTEM_HEALTH_READ.value)
    with pytest.raises(AuthenticationRequiredError):
        svc.require_permission(ctx, Permission.SYSTEM_HEALTH_READ.value)


def test_unknown_permission():
    svc = PermissionService()
    ctx = _ctx(*all_permissions())
    assert not svc.has_permission(ctx, "not.a.real.permission")
    with pytest.raises(UnknownPermissionError):
        svc.require_permission(ctx, "not.a.real.permission")


def test_require_denied():
    svc = PermissionService()
    ctx = _ctx(Permission.SYSTEM_HEALTH_READ.value)
    with pytest.raises(PermissionDeniedError):
        svc.require_permission(ctx, Permission.SYSTEM_LOGS_READ.value)


def test_super_admin_style_context():
    svc = PermissionService()
    ctx = PermissionContext(
        user_id=1,
        is_authenticated=True,
        is_super_admin=True,
        permissions=all_permissions(),
    )
    for p in (
        Permission.SYSTEM_HEALTH_READ.value,
        Permission.BILLING_REFUND.value,
        Permission.VAULT_SECRETS_MANAGE.value,
    ):
        assert svc.has_permission(ctx, p)
        svc.require_permission(ctx, p)
