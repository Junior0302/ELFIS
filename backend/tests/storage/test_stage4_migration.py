"""Tests migration / intégrité / registry supabase (mock)."""

from __future__ import annotations

import io

import httpx
import pytest

from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.providers.supabase_http_client import SupabaseStorageHttpClient
from app.storage.providers.supabase_storage_provider import SupabaseStorageProvider
from app.storage.storage_context import StorageContext
from app.storage.storage_migration_service import StorageMigrationService
from app.storage.storage_integrity_service import StorageIntegrityService
from app.storage.storage_registry import clear_storage_provider_cache
from app.storage.document_registry_service import DocumentRegistryService
from tests.storage.conftest_helpers import make_storage_db, seed_org_user


def _sb_provider():
    store: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and "/object/" in path and "/list/" not in path:
            key = path.split("/object/", 1)[1]
            store[key] = request.read()
            return httpx.Response(200, json={})
        if request.method == "GET" and "/object/" in path:
            key = path.split("/object/", 1)[1]
            if key not in store:
                return httpx.Response(404)
            return httpx.Response(200, content=store[key])
        if request.method == "DELETE":
            return httpx.Response(200)
        if "/list/" in path:
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    client = SupabaseStorageHttpClient(
        base_url="https://example.supabase.co",
        service_role_key="k",
        transport=httpx.MockTransport(handler),
        max_retries=0,
    )
    return SupabaseStorageProvider(client=client, bucket="elfis-documents"), store


@pytest.fixture
def env(tmp_path, monkeypatch):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    root = tmp_path / "obj"
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
    yield db, org, user, root
    db.close()


def test_remote_upload_pipeline_via_os_temp(env, monkeypatch):
    db, org, user, root = env
    sb, store = _sb_provider()
    monkeypatch.setattr("app.config.settings.storage_provider", "supabase")
    monkeypatch.setattr(
        "app.storage.storage_service.default_storage_context",
        lambda namespace="default": StorageContext(provider=sb, namespace=namespace),
    )
    clear_storage_provider_cache()
    registry = DocumentRegistryService(db, context=StorageContext(provider=sb))
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=b"%PDF-1.4 remote\n%%EOF",
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    assert doc.current_storage_object_id
    obj = registry.get_storage_object(doc)
    assert obj is not None
    assert obj.provider == "supabase"
    assert any(store.values())


def test_migration_local_to_supabase(env):
    db, org, user, root = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=b"%PDF-1.4 mig\n%%EOF",
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    obj = registry.get_storage_object(doc)
    assert obj and obj.provider == "local"
    sb, _ = _sb_provider()
    local = LocalStorageProvider(root=root)
    svc = StorageMigrationService(db, source=local, target=sb)
    mig = svc.migrate_one(obj, to_provider="supabase", dry_run=False, keep_source=True)
    assert mig.status == "switched"
    db.refresh(obj)
    assert obj.provider == "supabase"


def test_integrity_metadata(env):
    db, org, user, _ = env
    registry = DocumentRegistryService(db)
    registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=b"%PDF-1.4 int\n%%EOF",
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    report = StorageIntegrityService(db).verify(provider="local", limit=10, preview=True)
    assert report.scanned >= 1
    assert report.ok >= 1
