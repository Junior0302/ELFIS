"""Tests repositories / modèles."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.storage.storage_models import ElfisDocumentLink, ElfisDocumentRecord, ElfisStorageObject
from app.storage.storage_repository import DocumentLinkRepository, DocumentRepository, StorageObjectRepository
from app.storage.storage_types import DocumentStatus, StorageObjectStatus
from tests.storage.conftest_helpers import make_storage_db, seed_org_user


def test_create_storage_object_and_document():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace="default",
        object_key=f"{uuid4().hex}.txt",
        original_filename="note.txt",
        safe_filename="note.txt",
        mime_type_declared="text/plain",
        size_bytes=5,
        status=StorageObjectStatus.AVAILABLE.value,
        organization_id=org.id,
        created_by_user_id=user.id,
    )
    StorageObjectRepository(db).create(obj, commit=True)
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="Note",
        organization_id=org.id,
        current_storage_object_id=obj.id,
        owner_user_id=user.id,
        status=DocumentStatus.AVAILABLE.value,
        source="upload",
    )
    DocumentRepository(db).create(doc, commit=True)
    got = DocumentRepository(db).get(doc.id)
    assert got is not None
    assert got.organization_id == org.id
    assert got.current_storage_object_id == obj.id


def test_unique_object_key():
    factory, _ = make_storage_db()
    db = factory()
    org, _ = seed_org_user(db)
    key = f"{uuid4().hex}.bin"
    for _ in range(2):
        row = ElfisStorageObject(
            id=str(uuid4()),
            provider="local",
            namespace="default",
            object_key=key,
            original_filename="a.bin",
            safe_filename="a.bin",
            size_bytes=1,
            status="available",
            organization_id=org.id,
        )
        db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()


def test_archive_logical():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="Archivable",
        organization_id=org.id,
        owner_user_id=user.id,
        status=DocumentStatus.AVAILABLE.value,
    )
    DocumentRepository(db).create(doc, commit=True)
    archived = DocumentRepository(db).archive(doc.id, commit=True)
    assert archived.status == DocumentStatus.ARCHIVED.value
    assert archived.archived_at is not None
    listed = DocumentRepository(db).list_for_organization(org.id, include_archived=False)
    assert all(d.id != doc.id for d in listed[0])


def test_link_uniqueness():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="L",
        organization_id=org.id,
        status="available",
    )
    DocumentRepository(db).create(doc, commit=True)
    link = ElfisDocumentLink(
        id=str(uuid4()),
        document_id=doc.id,
        entity_type="invoice",
        entity_id="42",
        relation_type="attachment",
        created_by_user_id=user.id,
    )
    DocumentLinkRepository(db).create(link, commit=True)
    dup = ElfisDocumentLink(
        id=str(uuid4()),
        document_id=doc.id,
        entity_type="invoice",
        entity_id="42",
        relation_type="attachment",
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
