"""Gardes de téléchargement — seul scan_status=clean est téléchargeable pour un user-upload."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.deps import AuthContext
from app.security.antivirus import (
    AntivirusError,
    AntivirusErrorCode,
    assert_scan_allows_download,
)
from app.storage.document_access_policy import DocumentAccessPolicy
from app.storage.storage_exceptions import DocumentAccessDeniedError
from app.storage.storage_models import ElfisDocumentRecord, ElfisStorageObject
from app.storage.storage_types import DocumentSource, DocumentStatus, StorageObjectStatus
from tests.storage.conftest_helpers import make_storage_db, seed_org_user
from tests.vault.test_vault_consult import _add_doc, _mock_storage, _seed, _session


def test_legacy_unknown_user_upload_download_forbidden():
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status="unknown", source="upload")
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED
    assert exc.value.http_status == 409
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status="unknown", content_origin="user_upload")
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED


def test_legacy_unknown_provenance_download_forbidden():
    """unknown n'est jamais traité comme generated_by_elfis."""
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status="unknown", content_origin="unknown")
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED
    assert exc.value.http_status == 409
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status="unknown", content_origin=None, source=None)
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status=None, content_origin="")
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED
    with pytest.raises(AntivirusError):
        assert_scan_allows_download(scan_status="pending", content_origin="unknown")
    with pytest.raises(AntivirusError):
        assert_scan_allows_download(scan_status="error", content_origin="unknown")


def test_legacy_generated_document_download_allowed():
    assert_scan_allows_download(
        scan_status="unknown",
        content_origin="generated_by_elfis",
    )


def test_new_generated_elfis_download_allowed():
    assert_scan_allows_download(
        scan_status="clean",
        content_origin="generated_by_elfis",
    )


def test_new_user_upload_clean_download_allowed():
    assert_scan_allows_download(scan_status="clean", content_origin="user_upload")


def test_unknown_origin_clean_download_allowed():
    assert_scan_allows_download(scan_status="clean", content_origin="unknown")
    assert_scan_allows_download(scan_status="clean", content_origin=None, source=None)


def test_unknown_provenance_non_unknown_scan_refused():
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status="unavailable", content_origin="unknown")
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED


def test_infected_refused_regardless_of_origin():
    with pytest.raises(AntivirusError) as exc:
        assert_scan_allows_download(scan_status="infected", content_origin="generated_by_elfis")
    assert exc.value.code == AntivirusErrorCode.FILE_INFECTED
    with pytest.raises(AntivirusError):
        assert_scan_allows_download(scan_status="infected", content_origin="unknown")


def test_generated_by_elfis_download_allowed_without_clean():
    assert_scan_allows_download(
        scan_status="unknown",
        content_origin="generated_by_elfis",
    )


def test_registry_unknown_user_upload_denied():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace="default",
        object_key="x.bin",
        original_filename="x.bin",
        safe_filename="x.bin",
        size_bytes=10,
        status=StorageObjectStatus.AVAILABLE.value,
        organization_id=org.id,
        scan_status="unknown",
    )
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="legacy",
        organization_id=org.id,
        status=DocumentStatus.AVAILABLE.value,
        source=DocumentSource.UPLOAD.value,
        current_storage_object_id=obj.id,
    )
    auth = AuthContext(
        user=user, organization_id=org.id, role="admin", permissions=["documents.download"]
    )
    with pytest.raises(DocumentAccessDeniedError) as exc:
        DocumentAccessPolicy().assert_can_download(auth, doc, obj)
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED


def test_registry_generated_unknown_allowed():
    factory, _ = make_storage_db()
    db = factory()
    org, user = seed_org_user(db)
    obj = ElfisStorageObject(
        id=str(uuid4()),
        provider="local",
        namespace="default",
        object_key="gen.pdf",
        original_filename="gen.pdf",
        safe_filename="gen.pdf",
        size_bytes=10,
        status=StorageObjectStatus.AVAILABLE.value,
        organization_id=org.id,
        scan_status="unknown",
    )
    doc = ElfisDocumentRecord(
        id=str(uuid4()),
        title="generated",
        organization_id=org.id,
        status=DocumentStatus.AVAILABLE.value,
        source=DocumentSource.GENERATED.value,
        current_storage_object_id=obj.id,
    )
    auth = AuthContext(
        user=user, organization_id=org.id, role="admin", permissions=["documents.download"]
    )
    DocumentAccessPolicy().assert_can_download(auth, doc, obj)


def test_vault_non_clean_no_signed_url():
    from app.services.vault.exceptions import VaultAntivirusError
    from app.services.vault.vault_service import create_download_url

    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="dirty")
    doc = db.query(__import__("app.models_vault", fromlist=["VaultDocument"]).VaultDocument).get("dirty")
    doc.scan_status = "unknown"
    doc.content_origin = "user_upload"
    db.add(doc)
    db.commit()
    storage = _mock_storage()
    with pytest.raises(VaultAntivirusError) as exc:
        create_download_url(
            db,
            user_id=user_id,
            organization_id=org_id,
            document_id="dirty",
            storage=storage,
        )
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED
    storage._client.create_signed_url.assert_not_called()


def test_vault_legacy_unknown_provenance_no_signed_url():
    from app.models_vault import VaultDocument
    from app.services.vault.exceptions import VaultAntivirusError
    from app.services.vault.vault_service import create_download_url

    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="legacy-unk")
    doc = db.get(VaultDocument, "legacy-unk")
    doc.scan_status = "unknown"
    doc.scan_engine = None
    doc.content_origin = "unknown"
    db.add(doc)
    db.commit()
    storage = _mock_storage()
    with pytest.raises(VaultAntivirusError) as exc:
        create_download_url(
            db,
            user_id=user_id,
            organization_id=org_id,
            document_id="legacy-unk",
            storage=storage,
        )
    assert exc.value.code == AntivirusErrorCode.FILE_SCAN_REQUIRED
    assert exc.value.http_status == 409
    storage._client.create_signed_url.assert_not_called()


def test_vault_new_generated_signed_url_allowed():
    from app.models_vault import VaultDocument
    from app.services.vault.vault_service import create_download_url

    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="gen-new")
    doc = db.get(VaultDocument, "gen-new")
    doc.scan_status = "clean"
    doc.scan_engine = "elfis_generated"
    doc.content_origin = "generated_by_elfis"
    db.add(doc)
    db.commit()
    storage = _mock_storage()
    resp = create_download_url(
        db,
        user_id=user_id,
        organization_id=org_id,
        document_id="gen-new",
        storage=storage,
    )
    assert resp.download_url
    storage._client.create_signed_url.assert_called_once()


def test_vault_infected_no_signed_url():
    from app.services.vault.exceptions import VaultAntivirusError
    from app.services.vault.vault_service import create_download_url

    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="inf")
    from app.models_vault import VaultDocument

    doc = db.query(VaultDocument).get("inf")
    doc.scan_status = "infected"
    db.add(doc)
    db.commit()
    storage = _mock_storage()
    with pytest.raises(VaultAntivirusError):
        create_download_url(
            db,
            user_id=user_id,
            organization_id=org_id,
            document_id="inf",
            storage=storage,
        )
    storage._client.create_signed_url.assert_not_called()
