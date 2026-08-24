"""Tests DocumentAccessPolicy + téléchargement quarantaine."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.deps import AuthContext
from app.storage.document_access_policy import DocumentAccessPolicy
from app.storage.storage_exceptions import DocumentAccessDeniedError
from app.storage.storage_models import ElfisDocumentRecord, ElfisStorageObject
from app.storage.storage_types import DocumentStatus, StorageObjectStatus
from tests.storage.conftest_helpers import make_storage_db, seed_org_user


def _auth(user, org_id, perms):
    return AuthContext(user=user, organization_id=org_id, role="admin", permissions=perms)


def test_cross_tenant_denied():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    policy = DocumentAccessPolicy()
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="x",
        organization_id=org.id + 99,
        status=DocumentStatus.AVAILABLE.value,
    )
    with pytest.raises(DocumentAccessDeniedError):
        policy.assert_can_read(_auth(user, org.id, ["documents.read"]), doc)


def test_quarantine_requires_special_perm():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    policy = DocumentAccessPolicy()
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="q",
        organization_id=org.id,
        status=DocumentStatus.FAILED.value,
    )
    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace="quarantine",
        object_key="x.bin",
        original_filename="x.bin",
        safe_filename="x.bin",
        size_bytes=10,
        status=StorageObjectStatus.QUARANTINED.value,
        organization_id=org.id,
    )
    with pytest.raises(DocumentAccessDeniedError):
        policy.assert_can_download(_auth(user, org.id, ["documents.download"]), doc, obj)
    policy.assert_can_download(
        _auth(user, org.id, ["documents.download", "storage.quarantine.read"]),
        doc,
        obj,
    )


def test_org_spoof_rejected():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    policy = DocumentAccessPolicy()
    from app.storage.storage_exceptions import StorageValidationError

    with pytest.raises(StorageValidationError):
        policy.resolve_organization_id(
            _auth(user, org.id, ["documents.create"]),
            requested_organization_id=org.id + 1,
        )
