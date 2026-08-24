"""Tests lifecycle / legal hold / rétention / purge RC2.4 étape 3."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.storage.document_legal_hold_service import DocumentLegalHoldService
from app.storage.document_registry_service import DocumentRegistryService
from app.storage.document_retention_service import DocumentRetentionService
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext
from app.storage.storage_exceptions import StorageValidationError
from app.storage.storage_registry import clear_storage_provider_cache
from app.storage.storage_types import DocumentRelationType, DocumentStatus
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
    yield db, org, user, root
    db.close()


def _upload(db, org, user):
    svc = DocumentRegistryService(db)
    doc = svc.create_from_upload(
        organization_id=org.id,
        filename="a.pdf",
        content=b"%PDF-1.4 life\n%%EOF",
        declared_mime="application/pdf",
        owner_user_id=user.id,
    )
    return svc, doc


def test_archive_unarchive(env):
    db, org, user, _ = env
    svc, doc = _upload(db, org, user)
    archived = svc.archive(document_id=doc.id, organization_id=org.id)
    assert archived.status == DocumentStatus.ARCHIVED.value
    restored = svc.unarchive(document_id=doc.id, organization_id=org.id)
    assert restored.status == DocumentStatus.AVAILABLE.value


def test_invalid_unarchive_from_available(env):
    db, org, user, _ = env
    svc, doc = _upload(db, org, user)
    with pytest.raises(StorageValidationError):
        svc.unarchive(document_id=doc.id, organization_id=org.id)


def test_soft_delete_hides_and_blocks_download(env):
    db, org, user, _ = env
    svc, doc = _upload(db, org, user)
    svc.soft_delete(document_id=doc.id, organization_id=org.id, actor_user_id=user.id)
    items, total = svc.list_for_organization(org.id)
    assert total == 0
    assert all(i.id != doc.id for i in items)
    from app.deps import AuthContext
    from app.storage.document_access_policy import DocumentAccessPolicy

    auth = AuthContext(
        user=user,
        organization_id=org.id,
        role="admin",
        permissions=["documents.download", "documents.read"],
    )
    db.refresh(doc)
    obj = svc.get_storage_object(doc)
    with pytest.raises(Exception):
        DocumentAccessPolicy().assert_can_download(auth, doc, obj)


def test_restore_soft_deleted(env):
    db, org, user, _ = env
    svc, doc = _upload(db, org, user)
    svc.soft_delete(document_id=doc.id, organization_id=org.id)
    row = svc.restore_soft_deleted(document_id=doc.id, organization_id=org.id)
    assert row.status == DocumentStatus.AVAILABLE.value
    assert row.deleted_at is None


def test_legal_hold_place_release_idempotent(env):
    db, org, user, _ = env
    _, doc = _upload(db, org, user)
    holds = DocumentLegalHoldService(db)
    hold = holds.place(
        document_id=doc.id,
        organization_id=org.id,
        reason="litige client",
        placed_by_user_id=user.id,
    )
    assert hold.active
    with pytest.raises(StorageValidationError):
        holds.place(document_id=doc.id, organization_id=org.id, reason="x")
    released = holds.release(
        document_id=doc.id, hold_id=hold.id, organization_id=org.id, released_by_user_id=user.id
    )
    assert released.active is False
    again = holds.release(
        document_id=doc.id, hold_id=hold.id, organization_id=org.id, released_by_user_id=user.id
    )
    assert again.active is False


def test_purge_blocked_by_legal_hold(env):
    db, org, user, root = env
    svc, doc = _upload(db, org, user)
    svc.soft_delete(document_id=doc.id, organization_id=org.id)
    db.refresh(doc)
    doc.retention_deadline = datetime.utcnow() - timedelta(days=1)
    db.commit()
    DocumentLegalHoldService(db).place(
        document_id=doc.id, organization_id=org.id, reason="hold purge", placed_by_user_id=user.id
    )
    ret = DocumentRetentionService(db, provider=LocalStorageProvider(root=root))
    decision = ret.explain_retention_decision(doc)
    assert decision.eligible is False
    assert decision.blocked_reason == "legal_hold"
    report = ret.purge_candidates(dry_run=False, batch_size=10)
    assert report["purged"] == 0


def test_purge_creates_tombstone(env):
    db, org, user, root = env
    svc, doc = _upload(db, org, user)
    oid = doc.current_storage_object_id
    svc.soft_delete(document_id=doc.id, organization_id=org.id)
    db.refresh(doc)
    doc.retention_deadline = datetime.utcnow() - timedelta(days=1)
    db.commit()
    ret = DocumentRetentionService(db, provider=LocalStorageProvider(root=root))
    report = ret.purge_candidates(dry_run=False, batch_size=10, reason="test_purge")
    assert report["purged"] == 1
    from app.storage.storage_repository import TombstoneRepository

    tomb = TombstoneRepository(db).get_by_document(doc.id)
    assert tomb is not None
    assert tomb.purge_reason == "test_purge"
    db.refresh(doc)
    assert doc.status == DocumentStatus.PURGED.value


def test_business_link_blocks_purge(env):
    db, org, user, root = env
    svc, doc = _upload(db, org, user)
    svc.link_entity(
        document_id=doc.id,
        organization_id=org.id,
        entity_type="invoice",
        entity_id="inv-1",
        relation_type=DocumentRelationType.INVOICE.value,
        created_by_user_id=user.id,
    )
    svc.soft_delete(document_id=doc.id, organization_id=org.id)
    db.refresh(doc)
    doc.retention_deadline = datetime.utcnow() - timedelta(days=1)
    db.commit()
    ret = DocumentRetentionService(db, provider=LocalStorageProvider(root=root))
    decision = ret.explain_retention_decision(doc)
    assert decision.eligible is False
    assert decision.blocked_reason == "active_business_link"


def test_retention_explain_recent_not_eligible(env):
    db, org, user, _ = env
    _, doc = _upload(db, org, user)
    ret = DocumentRetentionService(db)
    decision = ret.explain_retention_decision(doc)
    assert decision.eligible is False
    assert decision.blocked_reason == "status_not_deleted"
