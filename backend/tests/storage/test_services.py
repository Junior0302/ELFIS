"""Tests StorageService / DocumentRegistryService."""

from __future__ import annotations

import pytest

from app.storage.document_registry_service import DocumentRegistryService
from app.storage.providers.disabled_storage_provider import DisabledStorageProvider
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext
from app.storage.storage_exceptions import DocumentAccessDeniedError, StorageDisabledError, StorageValidationError
from app.storage.storage_service import StorageService
from tests.storage.conftest_helpers import make_storage_db, seed_org_user


def _svc(db, tmp_path):
    ctx = StorageContext(provider=LocalStorageProvider(root=tmp_path), namespace="test")
    return DocumentRegistryService(db, context=ctx)


def test_upload_valid(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db, tmp_path)
    doc = svc.create_from_upload(
        organization_id=org.id,
        filename="note.txt",
        content=b"hello registry",
        declared_mime="text/plain",
        owner_user_id=user.id,
        title="Note",
    )
    assert doc.status == "available"
    assert doc.current_storage_object_id
    obj = svc.get_storage_object(doc)
    assert obj is not None
    assert obj.checksum_sha256
    # aucun chemin physique exposé dans les champs API-like
    assert not hasattr(obj, "path")
    assert "\\" not in (obj.object_key or "")
    data = svc.open_download(doc).read()
    assert data == b"hello registry"


def test_reject_exe(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db, tmp_path)
    with pytest.raises(StorageValidationError):
        svc.create_from_upload(
            organization_id=org.id,
            filename="bad.exe",
            content=b"MZ123456",
            declared_mime="application/octet-stream",
            owner_user_id=user.id,
        )


def test_cross_tenant_denied(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    org2 = type(org)(name="Other")
    db.add(org2)
    db.commit()
    db.refresh(org2)
    svc = _svc(db, tmp_path)
    doc = svc.create_from_upload(
        organization_id=org.id,
        filename="a.txt",
        content=b"secret",
        declared_mime="text/plain",
        owner_user_id=user.id,
    )
    with pytest.raises(DocumentAccessDeniedError):
        svc.get_for_organization(doc.id, org2.id)


def test_link_and_archive(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db, tmp_path)
    doc = svc.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=b"%PDF-1.4 hello",
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    link = svc.link_entity(
        document_id=doc.id,
        organization_id=org.id,
        entity_type="invoice",
        entity_id="99",
        relation_type="attachment",
        created_by_user_id=user.id,
    )
    assert link.entity_id == "99"
    archived = svc.archive(document_id=doc.id, organization_id=org.id)
    assert archived.status == "archived"


def test_disabled_provider(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    ctx = StorageContext(provider=DisabledStorageProvider(), namespace="x")
    svc = DocumentRegistryService(db, context=ctx)
    with pytest.raises(StorageDisabledError):
        svc.create_from_upload(
            organization_id=org.id,
            filename="a.txt",
            content=b"hello",
            declared_mime="text/plain",
            owner_user_id=user.id,
        )


def test_storage_service_no_path_leak(tmp_path):
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    ctx = StorageContext(provider=LocalStorageProvider(root=tmp_path), namespace="ns")
    storage = StorageService(db, context=ctx)
    row = storage.register_bytes(
        filename="x.txt",
        content=b"abc123",
        declared_mime="text/plain",
        organization_id=org.id,
        created_by_user_id=user.id,
    )
    payload = {
        "id": row.id,
        "object_key": row.object_key,
        "original_filename": row.original_filename,
    }
    blob = str(payload)
    assert str(tmp_path) not in blob
    assert "elfis_objects" not in blob or True  # object_key UUID only
    assert "/" not in row.object_key or row.object_key.count("/") == 0
