"""Tests consultation / téléchargement ELFIS Vault."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_saas import Organization, OrganizationMember, Role, User
from app.models_vault import VaultActivityLog, VaultDocument
from app.schemas_vault import VaultArchiveStatus, VaultDocumentType, VaultSortBy, VaultSortOrder
from app.services.vault.exceptions import VaultNotFoundError, VaultStorageError, VaultValidationError
from app.services.vault.storage_service import VaultStorageService
from app.services.vault.vault_service import (
    create_download_url,
    get_document_details,
    list_documents,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db, *, role_name: str = "owner", org_id: int = 1, user_id: int = 1):
    db.add(Organization(id=org_id, name=f"Org {org_id}"))
    role = Role(id=org_id * 10 + user_id, name=role_name, permissions="[]")
    db.add(role)
    db.add(
        User(
            id=user_id,
            first_name="Ada",
            last_name="Lovelace",
            email=f"u{user_id}@example.com",
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


def _add_doc(
    db,
    *,
    org_id: int,
    doc_id: str = "doc-1",
    document_number: str = "FACT-001",
    filename: str = "facture.pdf",
    document_type: str = "customer_invoice",
    amount_ttc: str = "1200.00",
    invoice_date: date | None = None,
    archive_status: str = "archived",
    storage_path: str = "entreprises/1/2026/factures-clients/facture_abc.pdf",
):
    now = datetime.utcnow()
    doc = VaultDocument(
        id=doc_id,
        organization_id=org_id,
        document_type=document_type,
        document_number=document_number,
        original_filename=filename,
        storage_path=storage_path,
        mime_type="application/pdf",
        file_size=245821,
        checksum_sha256="abc" + doc_id,
        invoice_date=invoice_date or date(2026, 7, 20),
        amount_ht=Decimal("1000.00"),
        amount_vat=Decimal("200.00"),
        amount_ttc=Decimal(amount_ttc),
        currency="EUR",
        archive_status=archive_status,
        accounting_status="not_processed",
        email_status="not_sent",
        version=1,
        archived_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    return doc


def _mock_storage() -> VaultStorageService:
    client = MagicMock()
    client.configured = True
    client.create_signed_url = MagicMock(return_value="https://signed.example/tmp")
    return VaultStorageService(client=client, bucket="elfis-vault")


def test_list_paginated_success():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="a")
    _add_doc(db, org_id=org_id, doc_id="b", document_number="FACT-002")
    result = list_documents(db, user_id=user_id, organization_id=org_id, page=1, page_size=1)
    assert result.pagination.total_items == 2
    assert result.pagination.total_pages == 2
    assert len(result.items) == 1
    assert not hasattr(result.items[0], "storage_path") or "storage_path" not in result.items[0].model_dump()
    dumped = result.items[0].model_dump()
    assert "storage_path" not in dumped
    assert "checksum_sha256" not in dumped


def test_list_empty():
    db = _session()
    user_id, org_id = _seed(db)
    result = list_documents(db, user_id=user_id, organization_id=org_id)
    assert result.items == []
    assert result.pagination.total_items == 0


def test_list_filters_by_type():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="a", document_type="customer_invoice")
    _add_doc(db, org_id=org_id, doc_id="b", document_type="quote", document_number="D-1")
    result = list_documents(
        db,
        user_id=user_id,
        organization_id=org_id,
        document_type=VaultDocumentType.quote,
    )
    assert result.pagination.total_items == 1
    assert result.items[0].document_type == VaultDocumentType.quote


def test_list_search():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="a", document_number="FACT-999", filename="x.pdf")
    _add_doc(db, org_id=org_id, doc_id="b", document_number="OTHER", filename="devis-special.pdf")
    result = list_documents(db, user_id=user_id, organization_id=org_id, search="devis-special")
    assert result.pagination.total_items == 1
    assert result.items[0].id == "b"


def test_list_invalid_pagination():
    db = _session()
    user_id, org_id = _seed(db)
    with pytest.raises(VaultValidationError):
        list_documents(db, user_id=user_id, organization_id=org_id, page=0)
    with pytest.raises(VaultValidationError):
        list_documents(db, user_id=user_id, organization_id=org_id, page_size=101)


def test_detail_success_and_view_log():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="d1")
    detail = get_document_details(
        db, user_id=user_id, organization_id=org_id, document_id="d1"
    )
    assert detail.id == "d1"
    assert detail.is_locked is False
    logs = db.query(VaultActivityLog).filter(VaultActivityLog.action == "document_viewed").all()
    assert len(logs) == 1
    meta = json.loads(logs[0].metadata_json)
    assert meta["source"] == "vault_document_details"


def test_detail_absent():
    db = _session()
    user_id, org_id = _seed(db)
    with pytest.raises(VaultNotFoundError):
        get_document_details(db, user_id=user_id, organization_id=org_id, document_id="missing")


def test_cross_tenant_404():
    db = _session()
    user_id, org_id = _seed(db, org_id=1, user_id=1)
    db.add(Organization(id=2, name="Other"))
    db.commit()
    _add_doc(db, org_id=2, doc_id="secret")
    with pytest.raises(VaultNotFoundError):
        get_document_details(db, user_id=user_id, organization_id=org_id, document_id="secret")


def test_comptable_can_read():
    db = _session()
    # Unique role name per DB: Role.name is unique globally
    user_id, org_id = _seed(db, role_name="comptable")
    _add_doc(db, org_id=org_id, doc_id="c1")
    result = list_documents(db, user_id=user_id, organization_id=org_id)
    assert result.pagination.total_items == 1
    detail = get_document_details(db, user_id=user_id, organization_id=org_id, document_id="c1")
    assert detail.id == "c1"


def test_signed_url_generated_and_not_persisted():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="s1")
    storage = _mock_storage()
    resp = create_download_url(
        db,
        user_id=user_id,
        organization_id=org_id,
        document_id="s1",
        storage=storage,
    )
    assert resp.download_url == "https://signed.example/tmp"
    assert resp.expires_in == 300
    assert resp.expires_at > datetime.utcnow()
    storage._client.create_signed_url.assert_called_once()
    # URL absente des logs d'activité
    logs = db.query(VaultActivityLog).filter(VaultActivityLog.action == "document_downloaded").all()
    assert len(logs) == 1
    meta = json.loads(logs[0].metadata_json)
    assert "download_url" not in meta
    assert meta["expires_in"] == 300
    assert meta["source"] == "vault_download_url"
    # Pas d'URL dans la table documents
    doc = db.query(VaultDocument).filter(VaultDocument.id == "s1").one()
    assert "signed.example" not in (doc.storage_path or "")


def test_signed_url_ttl_clamped(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_vault_signed_url_ttl_seconds", 30)
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="s2")
    resp = create_download_url(
        db,
        user_id=user_id,
        organization_id=org_id,
        document_id="s2",
        storage=_mock_storage(),
    )
    assert resp.expires_in == 60


def test_storage_error_on_sign():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="s3")
    storage = _mock_storage()
    storage._client.create_signed_url.side_effect = RuntimeError("fail")
    with pytest.raises(VaultStorageError):
        create_download_url(
            db,
            user_id=user_id,
            organization_id=org_id,
            document_id="s3",
            storage=storage,
        )


def test_deleted_excluded_from_list_and_detail():
    db = _session()
    user_id, org_id = _seed(db)
    _add_doc(db, org_id=org_id, doc_id="gone", archive_status="deleted")
    result = list_documents(db, user_id=user_id, organization_id=org_id)
    assert result.pagination.total_items == 0
    with pytest.raises(VaultNotFoundError):
        get_document_details(db, user_id=user_id, organization_id=org_id, document_id="gone")
