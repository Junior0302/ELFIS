"""Tests API Document Registry."""

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


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    db.close()

    root = tmp_path / "objects"
    root.mkdir()
    monkeypatch.setattr(
        "app.storage.storage_registry.settings.storage_provider",
        "local",
    )
    monkeypatch.setattr(
        "app.storage.providers.local_storage_provider.settings.storage_local_root",
        str(root),
    )
    monkeypatch.setattr(
        "app.config.settings.storage_provider",
        "local",
    )
    monkeypatch.setattr(
        "app.config.settings.storage_local_root",
        str(root),
    )
    clear_storage_provider_cache()

    monkeypatch.setattr(
        "app.storage.storage_registry.LocalStorageProvider",
        lambda: LocalStorageProvider(root=root),
    )
    monkeypatch.setattr(
        "app.storage.storage_service.default_storage_context",
        lambda namespace="default": StorageContext(
            provider=LocalStorageProvider(root=root), namespace=namespace
        ),
    )

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


def _auth(user, org, permissions):
    return AuthContext(user=user, organization_id=org.id, role="admin", permissions=permissions)


def test_401_unauthenticated(api_env):
    app, factory, org, user, _ = api_env

    def deny():
        from fastapi import HTTPException

        raise HTTPException(401, detail="Authentification requise")

    app.dependency_overrides[get_auth_context] = deny
    client = TestClient(app)
    assert client.get("/api/document-registry").status_code == 401


def test_403_missing_permission(api_env):
    app, factory, org, user, _ = api_env
    app.dependency_overrides[get_auth_context] = lambda: _auth(user, org, ["invoice.read"])
    client = TestClient(app)
    assert client.get("/api/document-registry").status_code == 403


def test_upload_list_get_download_archive(api_env):
    app, factory, org, user, root = api_env
    perms = ["documents.read", "documents.write", "documents.create", "documents.download", "documents.archive"]
    app.dependency_overrides[get_auth_context] = lambda: _auth(user, org, perms)
    client = TestClient(app)

    files = {"file": ("note.txt", BytesIO(b"hello registry api"), "text/plain")}
    data = {"title": "API Note", "document_type": "file", "source": "upload"}
    res = client.post("/api/document-registry", files=files, data=data)
    assert res.status_code == 201, res.text
    body = res.json()
    doc_id = body["id"]
    assert body["title"] == "API Note"
    assert body["organization_id"] == org.id
    assert "object_key" not in res.text or body.get("storage_object", {}).get("object_key")
    # pas de chemin physique
    assert str(root) not in res.text
    assert ":\\" not in res.text.lower()

    listed = client.get("/api/document-registry")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    one = client.get(f"/api/document-registry/{doc_id}")
    assert one.status_code == 200
    assert one.json()["id"] == doc_id

    dl = client.get(f"/api/document-registry/{doc_id}/download")
    assert dl.status_code == 200
    assert dl.content == b"hello registry api"
    cd = dl.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "note.txt" in cd
    assert dl.headers.get("content-type", "").startswith("text/plain")

    link = client.post(
        f"/api/document-registry/{doc_id}/links",
        json={"entity_type": "invoice", "entity_id": "7", "relation_type": "attachment"},
    )
    assert link.status_code == 201

    arch = client.post(f"/api/document-registry/{doc_id}/archive")
    assert arch.status_code == 200
    assert arch.json()["status"] == "archived"


def test_wrong_org_404(api_env):
    app, factory, org, user, _ = api_env
    perms = ["documents.read", "documents.write", "documents.create", "documents.download"]
    app.dependency_overrides[get_auth_context] = lambda: _auth(user, org, perms)
    client = TestClient(app)
    files = {"file": ("a.txt", BytesIO(b"secret"), "text/plain")}
    created = client.post("/api/document-registry", files=files, data={"title": "S"})
    assert created.status_code == 201
    doc_id = created.json()["id"]

    # autre org
    db = factory()
    from app.models_saas import Organization

    other = Organization(name="Other Org")
    db.add(other)
    db.commit()
    db.refresh(other)
    db.close()

    app.dependency_overrides[get_auth_context] = lambda: _auth(user, other, perms)
    client2 = TestClient(app)
    res = client2.get(f"/api/document-registry/{doc_id}")
    assert res.status_code == 404


def test_content_disposition_safe(api_env):
    app, factory, org, user, _ = api_env
    perms = ["documents.read", "documents.write", "documents.create", "documents.download"]
    app.dependency_overrides[get_auth_context] = lambda: _auth(user, org, perms)
    client = TestClient(app)
    files = {"file": ('rapport "final".pdf', BytesIO(b"%PDF-1.4 xx"), "application/pdf")}
    created = client.post("/api/document-registry", files=files, data={"title": "R"})
    assert created.status_code == 201
    doc_id = created.json()["id"]
    dl = client.get(f"/api/document-registry/{doc_id}/download")
    assert dl.status_code == 200
    cd = dl.headers["content-disposition"]
    assert "attachment" in cd
    assert "\n" not in cd
