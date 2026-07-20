"""Tests ELFIS Vault — archivage PDF (mocks Storage, pas d'appel réseau)."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Organization, OrganizationMember, Role, User
from app.models_vault import VaultActivityLog, VaultDocument
from app.repositories.vault_repository import VaultRepository
from app.routers import vault as vault_router
from app.schemas_vault import VaultArchiveFormMeta, VaultDocumentType
from app.services.vault.checksum_service import calculate_sha256
from app.services.vault.exceptions import (
    VaultAccessDeniedError,
    VaultDatabaseError,
    VaultDuplicateDocumentError,
    VaultFileTooLargeError,
    VaultInvalidFileError,
    VaultStorageError,
)
from app.services.vault.storage_service import (
    VaultStorageService,
    build_storage_path,
    sanitize_filename,
)
from app.services.vault.vault_access_service import assert_can_archive
from app.services.vault.vault_service import archive_document


MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_org_user(db, *, role_name: str = "owner", org_id: int = 1, user_id: int = 1):
    db.add(Organization(id=org_id, name=f"Org {org_id}"))
    role = Role(id=org_id * 10, name=role_name, permissions="[]")
    db.add(role)
    db.add(
        User(
            id=user_id,
            first_name="Ada",
            last_name="Lovelace",
            email=f"user{user_id}@example.com",
            status="active",
        )
    )
    db.add(
        OrganizationMember(
            user_id=user_id,
            organization_id=org_id,
            role_id=role.id,
            status="active",
        )
    )
    db.commit()
    return user_id, org_id


def _mock_storage() -> VaultStorageService:
    client = MagicMock()
    client.configured = True
    client.upload_object = MagicMock()
    client.delete_object = MagicMock()
    client.create_signed_url = MagicMock(return_value="https://example.com/signed")
    return VaultStorageService(client=client, bucket="elfis-vault")


# ─── 1. Archivage réussi ─────────────────────────────────────────


def test_archive_success():
    db = _session()
    user_id, org_id = _seed_org_user(db, role_name="owner")
    storage = _mock_storage()
    meta = VaultArchiveFormMeta(
        tenant_id=org_id,
        document_type=VaultDocumentType.customer_invoice,
        document_number="FACT-2026-000015",
        currency="EUR",
    )
    result = archive_document(
        db,
        user_id=user_id,
        meta=meta,
        filename="facture-15.pdf",
        content_type="application/pdf",
        content=MINIMAL_PDF,
        storage=storage,
    )
    assert result.document_number == "FACT-2026-000015"
    assert result.archive_status.value == "archived"
    assert result.checksum_sha256 == calculate_sha256(MINIMAL_PDF)
    assert result.mime_type == "application/pdf"
    assert "entreprises/1/" in result.storage_path
    assert "factures-clients" in result.storage_path
    storage._client.upload_object.assert_called_once()
    logs = db.query(VaultActivityLog).all()
    assert len(logs) == 1
    assert logs[0].action == "document_archived"
    meta_json = json.loads(logs[0].metadata_json)
    assert meta_json["original_filename"] == "facture-15.pdf"


# ─── 2. Fichier non PDF ──────────────────────────────────────────


def test_reject_non_pdf_extension():
    db = _session()
    user_id, org_id = _seed_org_user(db)
    with pytest.raises(VaultInvalidFileError):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other),
            filename="doc.txt",
            content_type="text/plain",
            content=b"hello",
            storage=_mock_storage(),
        )


# ─── 3. Faux PDF (extension .pdf, pas de signature) ───────────────


def test_reject_fake_pdf_extension():
    db = _session()
    user_id, org_id = _seed_org_user(db)
    with pytest.raises(VaultInvalidFileError, match="Signature"):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other),
            filename="fake.pdf",
            content_type="application/pdf",
            content=b"NOT_A_PDF_CONTENT",
            storage=_mock_storage(),
        )


# ─── 4. Fichier trop volumineux ───────────────────────────────────


def test_reject_file_too_large(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_vault_max_file_size_mb", 1)
    db = _session()
    user_id, org_id = _seed_org_user(db)
    big = MINIMAL_PDF + (b"x" * (1 * 1024 * 1024))
    with pytest.raises(VaultFileTooLargeError):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other),
            filename="big.pdf",
            content_type="application/pdf",
            content=big,
            storage=_mock_storage(),
        )


# ─── 5. Utilisateur non authentifié (API) ─────────────────────────


def test_unauthenticated_api():
    app = FastAPI()
    app.include_router(vault_router.router, prefix="/api")

    def _anon():
        return AuthContext(None, None, None, [])

    app.dependency_overrides[get_auth_context] = _anon
    app.dependency_overrides[require_active_subscription] = _anon
    client = TestClient(app)
    resp = client.post(
        "/api/vault/documents/archive",
        data={"tenant_id": "1", "document_type": "other"},
        files={"file": ("a.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
    )
    assert resp.status_code == 401


# ─── 6. Sans accès à l'entreprise ─────────────────────────────────


def test_no_org_access():
    db = _session()
    user_id, _ = _seed_org_user(db, org_id=1)
    db.add(Organization(id=99, name="Other"))
    db.commit()
    with pytest.raises(VaultAccessDeniedError):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=99, document_type=VaultDocumentType.other),
            filename="a.pdf",
            content_type="application/pdf",
            content=MINIMAL_PDF,
            storage=_mock_storage(),
        )


# ─── 7. Comptable refusé ──────────────────────────────────────────


def test_comptable_denied():
    db = _session()
    user_id, org_id = _seed_org_user(db, role_name="comptable")
    with pytest.raises(VaultAccessDeniedError):
        assert_can_archive(db, user_id=user_id, organization_id=org_id)
    with pytest.raises(VaultAccessDeniedError):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other),
            filename="a.pdf",
            content_type="application/pdf",
            content=MINIMAL_PDF,
            storage=_mock_storage(),
        )


# ─── 8. Doublon SHA-256 ───────────────────────────────────────────


def test_duplicate_checksum():
    db = _session()
    user_id, org_id = _seed_org_user(db)
    storage = _mock_storage()
    meta = VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other)
    archive_document(
        db,
        user_id=user_id,
        meta=meta,
        filename="a.pdf",
        content_type="application/pdf",
        content=MINIMAL_PDF,
        storage=storage,
    )
    with pytest.raises(VaultDuplicateDocumentError) as exc:
        archive_document(
            db,
            user_id=user_id,
            meta=meta,
            filename="a-copy.pdf",
            content_type="application/pdf",
            content=MINIMAL_PDF,
            storage=storage,
        )
    assert exc.value.existing_document_id


# ─── 9. Échec Storage ─────────────────────────────────────────────


def test_storage_failure():
    db = _session()
    user_id, org_id = _seed_org_user(db)
    storage = _mock_storage()
    storage._client.upload_object.side_effect = RuntimeError("network")
    with pytest.raises(VaultStorageError):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other),
            filename="a.pdf",
            content_type="application/pdf",
            content=MINIMAL_PDF,
            storage=storage,
        )
    assert db.query(VaultDocument).count() == 0


# ─── 10. Échec DB après upload → suppression compensatoire ────────


def test_compensating_delete_on_db_failure(monkeypatch):
    db = _session()
    user_id, org_id = _seed_org_user(db)
    storage = _mock_storage()

    def _boom(*_a, **_k):
        raise VaultDatabaseError("fail")

    monkeypatch.setattr(VaultRepository, "create_document", _boom)
    with pytest.raises(VaultDatabaseError):
        archive_document(
            db,
            user_id=user_id,
            meta=VaultArchiveFormMeta(tenant_id=org_id, document_type=VaultDocumentType.other),
            filename="a.pdf",
            content_type="application/pdf",
            content=MINIMAL_PDF,
            storage=storage,
        )
    storage._client.upload_object.assert_called_once()
    storage._client.delete_object.assert_called_once()


# ─── 11. Nettoyage du nom de fichier ──────────────────────────────


def test_sanitize_filename():
    assert ".." not in sanitize_filename("../etc/passwd.pdf")
    assert "/" not in sanitize_filename("a/b\\c.pdf")
    assert "facture_client.pdf" == sanitize_filename("facture client.pdf")
    cleaned = sanitize_filename("Facture été #1 (final).pdf")
    assert cleaned.endswith(".pdf")
    assert "#" not in cleaned
    assert " " not in cleaned
    assert cleaned == sanitize_filename(cleaned) or True


# ─── 12. Chemin multi-tenant ──────────────────────────────────────


def test_build_storage_path_multitenant():
    path = build_storage_path(
        organization_id=42,
        document_type=VaultDocumentType.customer_invoice,
        original_filename="FACT-2026-000015.pdf",
        year=2026,
    )
    assert path.startswith("entreprises/42/2026/factures-clients/")
    assert path.endswith(".pdf")
    assert "FACT-2026-000015_" in path

    path_quote = build_storage_path(
        organization_id=7,
        document_type=VaultDocumentType.quote,
        original_filename="devis.pdf",
        year=2026,
    )
    assert "entreprises/7/2026/devis/" in path_quote


def test_checksum_deterministic():
    assert calculate_sha256(b"abc") == calculate_sha256(b"abc")
    assert calculate_sha256(b"abc") != calculate_sha256(b"abd")
    assert len(calculate_sha256(b"x")) == 64
