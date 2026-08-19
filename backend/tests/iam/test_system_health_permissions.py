"""Intégration System Health × IAM."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context
from app.iam.permission_resolver import PermissionResolver
from app.iam.role_permission_map import PLATFORM_ADMIN_PERMISSIONS
from app.routers import admin_system_health
from app.system_health.health_registry import reset_default_registry_for_tests


def test_system_health_routes_use_iam_permissions():
    reset_default_registry_for_tests()
    app = FastAPI()
    app.include_router(admin_system_health.router, prefix="/api")
    client = TestClient(app)

    mapping = {
        "/api/admin/system/health": Permission.SYSTEM_HEALTH_READ.value,
        "/api/admin/system/metrics": Permission.SYSTEM_METRICS_READ.value,
        "/api/admin/system/alerts": Permission.SYSTEM_ALERTS_READ.value,
        "/api/admin/system/logs": Permission.SYSTEM_LOGS_READ.value,
    }

    for path, needed in mapping.items():
        url = path + ("?period=24h" if "metrics" in path else "")

        app.dependency_overrides[get_permission_context] = lambda needed=needed: PermissionContext(
            user_id=1,
            is_authenticated=True,
            permissions=frozenset({needed}),
        )
        assert client.get(url).status_code == 200, path

        app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
            user_id=1,
            is_authenticated=True,
            permissions=frozenset(),
        )
        assert client.get(url).status_code == 403, path

    reset_default_registry_for_tests()


def test_platform_admin_mapping_covers_system_health():
    assert Permission.SYSTEM_HEALTH_READ.value in PLATFORM_ADMIN_PERMISSIONS
    assert Permission.SYSTEM_METRICS_READ.value in PLATFORM_ADMIN_PERMISSIONS
    assert Permission.SYSTEM_ALERTS_READ.value in PLATFORM_ADMIN_PERMISSIONS
    assert Permission.SYSTEM_LOGS_READ.value in PLATFORM_ADMIN_PERMISSIONS


def test_resolver_platform_admin_can_access_all_health_routes_conceptually():
    from types import SimpleNamespace

    ctx = PermissionResolver().resolve(
        user=SimpleNamespace(id=1, status="active"),
        is_platform_admin=True,
    )
    for p in (
        Permission.SYSTEM_HEALTH_READ.value,
        Permission.SYSTEM_METRICS_READ.value,
        Permission.SYSTEM_ALERTS_READ.value,
        Permission.SYSTEM_LOGS_READ.value,
    ):
        assert p in ctx.permissions
