"""Tests versions documentaires RC2.4 étape 3."""

from __future__ import annotations

import pytest

from app.storage.document_registry_service import DocumentRegistryService
from app.storage.document_version_service import DocumentVersionService
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext
from app.storage.storage_exceptions import DocumentAccessDeniedError, StorageValidationError
from app.storage.storage_registry import clear_storage_provider_cache
from app.storage.storage_types import DocumentStatus, DocumentVersionStatus
from tests.storage.conftest_helpers import make_storage_db, seed_org_user


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
    yield db, org, user, root, factory
    db.close()


def _pdf(n: int = 1) -> bytes:
    return b"%PDF-1.4 content-v" + str(n).encode() + b"\n%%EOF"


def test_version_1_on_upload(env):
    db, org, user, _, _ = env
    svc = DocumentRegistryService(db)
    doc = svc.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    assert doc.current_version_id
    ver = DocumentVersionService(db).get_version(doc.id, doc.current_version_id, org.id)
    assert ver.version_number == 1
    assert ver.status == DocumentVersionStatus.CURRENT.value
    assert ver.storage_object_id == doc.current_storage_object_id


def test_version_increment_and_supersede(env):
    db, org, user, _, _ = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    v1_id = doc.current_version_id
    vsvc = DocumentVersionService(db, storage=registry.storage)
    v2 = vsvc.add_version_from_chunks_sync(
        document_id=doc.id,
        organization_id=org.id,
        filename="b.pdf",
        chunks=[_pdf(2)],
        declared_mime="application/pdf",
        created_by_user_id=user.id,
        change_reason="replace",
    )
    assert v2.version_number == 2
    db.refresh(doc)
    assert doc.current_version_id == v2.id
    v1 = vsvc.get_version(doc.id, v1_id, org.id)
    assert v1.status == DocumentVersionStatus.SUPERSEDED.value
    assert v1.superseded_at is not None


def test_version_immutable_fields(env):
    db, org, user, _, _ = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    vsvc = DocumentVersionService(db)
    ver = vsvc.get_version(doc.id, doc.current_version_id, org.id)
    with pytest.raises(StorageValidationError):
        vsvc.assert_version_immutable(ver, {"checksum_sha256": "x"})
    with pytest.raises(StorageValidationError):
        vsvc.assert_version_immutable(ver, {"storage_object_id": "x"})


def test_historical_download_stream(env):
    db, org, user, _, _ = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    v1_id = doc.current_version_id
    vsvc = DocumentVersionService(db, storage=registry.storage)
    vsvc.add_version_from_chunks_sync(
        document_id=doc.id,
        organization_id=org.id,
        filename="b.pdf",
        chunks=[_pdf(2)],
        declared_mime="application/pdf",
        created_by_user_id=user.id,
    )
    v1 = vsvc.get_version(doc.id, v1_id, org.id)
    stream = registry.storage.open_stream(v1.storage_object_id)
    data = stream.read()
    stream.close()
    assert data.startswith(b"%PDF")


def test_cross_tenant_version_denied(env):
    db, org, user, _, factory = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    org2, _ = seed_org_user(db, email="other@test.local")
    vsvc = DocumentVersionService(db)
    with pytest.raises(DocumentAccessDeniedError):
        vsvc.list_versions(doc.id, org2.id)


def test_no_version_on_archived(env):
    db, org, user, _, _ = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    registry.archive(document_id=doc.id, organization_id=org.id)
    vsvc = DocumentVersionService(db, storage=registry.storage)
    with pytest.raises(StorageValidationError):
        vsvc.add_version_from_chunks_sync(
            document_id=doc.id,
            organization_id=org.id,
            filename="b.pdf",
            chunks=[_pdf(2)],
            declared_mime="application/pdf",
        )


def test_no_version_on_deleted(env):
    db, org, user, _, _ = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    registry.soft_delete(document_id=doc.id, organization_id=org.id, actor_user_id=user.id)
    vsvc = DocumentVersionService(db, storage=registry.storage)
    with pytest.raises((StorageValidationError, DocumentAccessDeniedError)):
        vsvc.add_version_from_chunks_sync(
            document_id=doc.id,
            organization_id=org.id,
            filename="b.pdf",
            chunks=[_pdf(2)],
            declared_mime="application/pdf",
        )


def test_restore_creates_new_version_strategy_b(env):
    db, org, user, _, _ = env
    registry = DocumentRegistryService(db)
    doc = registry.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=_pdf(1),
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    v1_id = doc.current_version_id
    vsvc = DocumentVersionService(db, storage=registry.storage)
    vsvc.add_version_from_chunks_sync(
        document_id=doc.id,
        organization_id=org.id,
        filename="b.pdf",
        chunks=[_pdf(2)],
        declared_mime="application/pdf",
    )
    restored = vsvc.restore_as_new_version(
        document_id=doc.id,
        organization_id=org.id,
        version_id=v1_id,
        created_by_user_id=user.id,
    )
    assert restored.version_number == 3
    v1 = vsvc.get_version(doc.id, v1_id, org.id)
    assert restored.storage_object_id == v1.storage_object_id
    assert restored.id != v1_id


def test_backfill_idempotent(env):
    db, org, user, _, _ = env
    from uuid import uuid4
    from app.storage.storage_models import ElfisDocumentRecord, ElfisStorageObject
    from app.storage.storage_types import StorageObjectStatus

    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace="default",
        object_key="k1",
        original_filename="legacy.pdf",
        safe_filename="legacy.pdf",
        size_bytes=10,
        status=StorageObjectStatus.AVAILABLE.value,
        organization_id=org.id,
        checksum_sha256="abc",
    )
    db.add(obj)
    db.flush()
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="legacy",
        status=DocumentStatus.AVAILABLE.value,
        organization_id=org.id,
        current_storage_object_id=obj.id,
        source="upload",
    )
    db.add(doc)
    db.commit()
    vsvc = DocumentVersionService(db)
    v1 = vsvc.create_initial_version(document=doc, storage_obj=obj, commit=True)
    v1b = vsvc.create_initial_version(document=doc, storage_obj=obj, commit=True)
    assert v1.id == v1b.id
    assert doc.current_version_id == v1.id
