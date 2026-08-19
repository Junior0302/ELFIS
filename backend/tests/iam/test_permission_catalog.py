"""Tests catalogue permissions."""

from __future__ import annotations

import pytest

from app.iam.permission_catalog import (
    Permission,
    all_permissions,
    assert_no_duplicate_permissions,
    is_known_permission,
    validate_permission,
)


def test_no_duplicates():
    assert_no_duplicate_permissions()


def test_known_permission_accepted():
    assert is_known_permission(Permission.SYSTEM_HEALTH_READ.value)
    assert validate_permission("system.health.read") == "system.health.read"


def test_unknown_permission_rejected():
    assert not is_known_permission("system.health.hack")
    with pytest.raises(ValueError, match="inconnue"):
        validate_permission("system.health.hack")


def test_format_resource_action():
    with pytest.raises(ValueError, match="format"):
        validate_permission("InvalidPermission")
    with pytest.raises(ValueError, match="format"):
        validate_permission("bad")
    perms = all_permissions()
    assert len(perms) >= 40
    for p in perms:
        assert "." in p
        assert p == p.lower()
