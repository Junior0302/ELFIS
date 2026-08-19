"""Tests API admin IAM."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.iam.permission_catalog import Permission, all_permissions
from app.iam.permission_context import PermissionContext
from app.iam.permission_dependencies import get_permission_context
from app.iam.system_roles import bootstrap_system_roles
from app.routers import admin_iam
from tests.iam.conftest_helpers import make_iam_db, seed_user


def _client_with_db(factory):
    from app.database import get_db

    app = FastAPI()
    app.include_router(admin_iam.router, prefix="/api")

    def _db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    return app


def test_unauthenticated_401():
    factory, _ = make_iam_db()
    app = _client_with_db(factory)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        is_authenticated=False
    )
    client = TestClient(app)
    assert client.get("/api/admin/iam/roles").status_code == 401


def test_forbidden_403():
    factory, _ = make_iam_db()
    app = _client_with_db(factory)
    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({"system.health.read"}),
    )
    client = TestClient(app)
    assert client.get("/api/admin/iam/roles").status_code == 403


def test_reader_and_manager():
    factory, _ = make_iam_db()
    db = factory()
    bootstrap_system_roles(db, commit=True)
    user = seed_user(db)
    db.close()

    app = _client_with_db(factory)

    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({Permission.SECURITY_PERMISSIONS_READ.value}),
    )
    client = TestClient(app)
    res = client.get("/api/admin/iam/roles")
    assert res.status_code == 200
    codes = {r["code"] for r in res.json()}
    assert "platform_admin" in codes
    assert "password" not in res.text.lower()

    # assign requires manage
    role_id = next(r["id"] for r in res.json() if r["code"] == "platform_viewer")
    assert client.post(f"/api/admin/iam/users/{user.id}/roles/{role_id}").status_code == 403

    app.dependency_overrides[get_permission_context] = lambda: PermissionContext(
        user_id=1,
        is_authenticated=True,
        permissions=frozenset({Permission.SECURITY_PERMISSIONS_MANAGE.value}),
    )
    assert client.post(f"/api/admin/iam/users/{user.id}/roles/{role_id}").status_code == 204
    roles = client.get(f"/api/admin/iam/users/{user.id}/roles")
    assert roles.status_code == 200
    assert any(r["code"] == "platform_viewer" for r in roles.json())

    perms = client.get(f"/api/admin/iam/users/{user.id}/permissions")
    assert perms.status_code == 200
    assert "system.health.read" in perms.json()["permissions"]
    # pas de dump catalogue complet forcé
    assert "jwt" not in perms.text.lower()

    assert client.delete(f"/api/admin/iam/users/{user.id}/roles/{role_id}").status_code == 204
