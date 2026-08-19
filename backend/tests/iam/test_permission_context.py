"""Tests PermissionContext."""

from __future__ import annotations

from app.iam.permission_context import PermissionContext


def test_context_has_permission():
    ctx = PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({"system.health.read"}),
    )
    assert ctx.has("system.health.read")
    assert not ctx.has("system.logs.read")


def test_anonymous_defaults():
    ctx = PermissionContext()
    assert ctx.is_authenticated is False
    assert ctx.permissions == frozenset()
    assert ctx.is_platform_admin is False
    assert ctx.is_super_admin is False
