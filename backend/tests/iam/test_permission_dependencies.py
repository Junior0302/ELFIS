"""Tests dépendances FastAPI IAM."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context, require_permission


def _app_with_perm(permission: str) -> FastAPI:
    app = FastAPI()

    @app.get("/secured")
    def secured(ctx: PermissionContext = Depends(require_permission(permission))):
        return {"user_id": ctx.user_id, "ok": True}

    return app


def test_unauthenticated_401():
    app = _app_with_perm(Permission.SYSTEM_HEALTH_READ.value)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        is_authenticated=False
    )
    client = TestClient(app)
    res = client.get("/secured")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "authentication_required"


def test_authenticated_without_permission_403():
    app = _app_with_perm(Permission.SYSTEM_HEALTH_READ.value)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=3,
        is_authenticated=True,
        permissions=frozenset({"jobs.read"}),
    )
    client = TestClient(app)
    res = client.get("/secured")
    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["code"] == "permission_denied"
    assert "jobs.read" not in res.text  # ne révèle pas les permissions internes
    assert "vault.secrets" not in res.text


def test_platform_admin_200():
    app = _app_with_perm(Permission.SYSTEM_HEALTH_READ.value)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        is_platform_admin=True,
        permissions=frozenset({Permission.SYSTEM_HEALTH_READ.value}),
    )
    client = TestClient(app)
    res = client.get("/secured")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_super_admin_200():
    from app.iam.permission_catalog import all_permissions

    app = _app_with_perm(Permission.VAULT_SECRETS_MANAGE.value)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        is_super_admin=True,
        permissions=all_permissions(),
    )
    client = TestClient(app)
    assert client.get("/secured").status_code == 200


def test_normal_user_403():
    app = _app_with_perm(Permission.SYSTEM_HEALTH_READ.value)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=9,
        is_authenticated=True,
        organization_role="organization_member",
        permissions=frozenset({"products.read"}),
    )
    client = TestClient(app)
    assert client.get("/secured").status_code == 403
