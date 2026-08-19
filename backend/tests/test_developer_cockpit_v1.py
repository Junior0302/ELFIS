"""Tests Platform Developer Cockpit V1 — IAM + endpoints sûrs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.deps import DEVELOPER_COCKPIT_PERMISSIONS
from app.iam.permission_catalog import Permission, assert_no_duplicate_permissions
from app.iam.permission_types import PlatformRole
from app.iam.role_permission_map import PLATFORM_ADMIN_PERMISSIONS, PLATFORM_ROLE_PERMISSIONS
from app.main import app


client = TestClient(app)


def test_developer_permissions_in_catalog():
    assert_no_duplicate_permissions()
    for code in (
        Permission.PLATFORM_DEVELOPER.value,
        Permission.PLATFORM_ENGINEER.value,
        Permission.PLATFORM_SRE.value,
        Permission.PLATFORM_CTO.value,
    ):
        assert code in {p.value for p in Permission}


def test_developer_roles_not_auto_on_platform_admin_permissions():
    """Les perms developer/* ne sont PAS dans PLATFORM_ADMIN_PERMISSIONS."""
    for code in (
        Permission.PLATFORM_DEVELOPER.value,
        Permission.PLATFORM_ENGINEER.value,
        Permission.PLATFORM_SRE.value,
        Permission.PLATFORM_CTO.value,
    ):
        assert code not in PLATFORM_ADMIN_PERMISSIONS


def test_developer_roles_mapped():
    assert PlatformRole.PLATFORM_DEVELOPER.value in PLATFORM_ROLE_PERMISSIONS
    assert Permission.PLATFORM_DEVELOPER.value in PLATFORM_ROLE_PERMISSIONS[
        PlatformRole.PLATFORM_DEVELOPER.value
    ]


def test_developer_cockpit_gate_permission_set():
    assert "platform.developer" in DEVELOPER_COCKPIT_PERMISSIONS
    assert "platform.admin" in DEVELOPER_COCKPIT_PERMISSIONS


def test_developer_endpoints_require_auth():
    for path in (
        "/api/platform/developer/meta",
        "/api/platform/developer/overview",
        "/api/platform/developer/config-status",
        "/api/platform/developer/diagnostics",
        "/api/platform/developer/database-summary",
        "/api/platform/developer/routes",
    ):
        res = client.get(path)
        assert res.status_code in (401, 403), path


def test_config_status_never_leaks_secret_values(monkeypatch):
    """Sans auth on ne peut pas lire ; avec structure, secrets = statut seulement."""
    # Structure unitaire via import direct
    from app.routers import developer_cockpit as mod

    assert hasattr(mod, "_secret_status")
    assert mod._secret_status("") == "missing"
    assert mod._secret_status("change-me") == "invalid"
    assert mod._secret_status("super-secret-value") == "configured"
