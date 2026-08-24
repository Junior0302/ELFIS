"""Tests API versions / lifecycle / legal hold — RC2.4 étape 3."""

from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.routers import document_registry
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext
from app.storage.storage_registry import clear_storage_provider_cache
from tests.storage.conftest_helpers import make_storage_db, seed_org_user

ALL_PERMS = [
    "documents.read",
    "documents.create",
    "documents.download",
    "documents.archive",
    "documents.versions.read",
    "documents.versions.create",
    "documents.delete",
    "documents.restore",
    "documents.legal_hold.read",
    "documents.legal_hold.manage",
    "documents.manage",
]


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    db.close()
    root = tmp_path / "objects"
    root.mkdir()
    monkeypatch.setattr("app.config.settings.storage_provider", "local")
    monkeypatch.setattr("app.config.settings.storage_local_root", str(root))
    monkeypatch.setattr(
        "app.storage.storage_service.default_storage_context",
        lambda namespace="default": StorageContext(
            provider=LocalStorageProvider(root=root), namespace=namespace
        ),
    )
    clear_storage_provider_cache()

    app = FastAPI()
    app.include_router(document_registry.router, prefix="/api")

    def _db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    from app.database import get_db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_active_subscription] = lambda: None
    return app, factory, org, user, root


def _auth(user, org, permissions=None):
    return AuthContext(
        user=user,
        organization_id=org.id,
        role="admin",
        permissions=permissions or ALL_PERMS,
    )


def _upload(client, app, user, org):
    app.dependency_overrides[get_auth_context] = lambda: _auth(user, org)
    return client.post(
        "/api/document-registry/upload",
        files={"file": ("a.pdf", BytesIO(b"%PDF-1.4 api\n%%EOF"), "application/pdf")},
        data={"document_type": "file"},
    )


def test_api_versions_flow(api_env):
    app, factory, org, user, _ = api_env
    client = TestClient(app)
    r = _upload(client, app, user, org)
    assert r.status_code == 201
    doc = r.json()
    assert doc.get("current_version_id")
    assert doc.get("version_count") == 1

    r2 = client.post(
        f"/api/document-registry/{doc['id']}/versions",
        files={"file": ("b.pdf", BytesIO(b"%PDF-1.4 v2\n%%EOF"), "application/pdf")},
        data={"change_reason": "update"},
    )
    assert r2.status_code == 201
    assert r2.json()["version_number"] == 2

    lst = client.get(f"/api/document-registry/{doc['id']}/versions")
    assert lst.status_code == 200
    assert lst.json()["total"] == 2

    v1 = [v for v in lst.json()["items"] if v["version_number"] == 1][0]
    dl = client.get(f"/api/document-registry/{doc['id']}/versions/{v1['id']}/download")
    assert dl.status_code == 200


def test_api_archive_delete_restore(api_env):
    app, factory, org, user, _ = api_env
    client = TestClient(app)
    doc = _upload(client, app, user, org).json()

    ar = client.post(f"/api/document-registry/{doc['id']}/archive")
    assert ar.status_code == 200
    assert ar.json()["status"] == "archived"

    un = client.post(f"/api/document-registry/{doc['id']}/unarchive")
    assert un.status_code == 200
    assert un.json()["status"] == "available"

    de = client.post(f"/api/document-registry/{doc['id']}/delete", json={"reason": "test"})
    assert de.status_code == 200
    assert de.json()["status"] == "deleted"

    lst = client.get("/api/document-registry")
    assert all(i["id"] != doc["id"] for i in lst.json()["items"])

    re = client.post(f"/api/document-registry/{doc['id']}/restore")
    assert re.status_code == 200
    assert re.json()["status"] == "available"


def test_api_legal_hold(api_env):
    app, factory, org, user, _ = api_env
    client = TestClient(app)
    doc = _upload(client, app, user, org).json()
    placed = client.post(
        f"/api/document-registry/{doc['id']}/legal-holds",
        json={"reason": "litige facture"},
    )
    assert placed.status_code == 201
    hold_id = placed.json()["id"]
    lst = client.get(f"/api/document-registry/{doc['id']}/legal-holds")
    assert lst.json()["total"] >= 1
    rel = client.post(f"/api/document-registry/{doc['id']}/legal-holds/{hold_id}/release")
    assert rel.status_code == 200
    assert rel.json()["active"] is False


def test_api_version_permission_denied(api_env):
    app, factory, org, user, _ = api_env
    client = TestClient(app)
    doc = _upload(client, app, user, org).json()
    app.dependency_overrides[get_auth_context] = lambda: _auth(
        user, org, permissions=["documents.read"]
    )
    r = client.post(
        f"/api/document-registry/{doc['id']}/versions",
        files={"file": ("b.pdf", BytesIO(b"%PDF-1.4\n%%EOF"), "application/pdf")},
    )
    assert r.status_code == 403
