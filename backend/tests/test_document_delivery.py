"""Tests DocumentDeliveryService (Vault + e-mail, mocks réseau)."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_saas import DocumentEmailLog, Organization, OrganizationMember, Role, SalesDocument, User
from app.models_vault import VaultActivityLog, VaultDocument
from app.services.document_delivery import (
    DocumentDeliveryError,
    DocumentDeliveryService,
    delivery_attachment_filename,
)
from app.services.vault.exceptions import VaultStorageError


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_full(
    db,
    *,
    role_name: str = "owner",
    org_id: int = 1,
    user_id: int = 1,
    doc_type: str = "facture",
    number: str | None = None,
):
    db.add(Organization(id=org_id, name=f"Org {org_id}", currency="EUR", email="org@example.com"))
    role = Role(id=org_id * 10 + user_id, name=role_name, permissions='["documents.send_email","*"]')
    db.add(role)
    db.add(
        User(
            id=user_id,
            first_name="A",
            last_name="B",
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
    if number is None:
        number = {
            "facture": "FACT-2026-0015",
            "devis": "DEV-2026-0001",
            "avoir": "AV-2026-0001",
        }.get(doc_type, "DOC-1")
    doc = SalesDocument(
        organization_id=org_id,
        doc_type=doc_type,
        number=number,
        issue_date="2026-07-20",
        due_date="2026-08-20",
        status="draft",
        customer_name="Client SA",
        customer_email="client@example.com",
        amount_ht=1000.0,
        amount_tva=200.0,
        amount_ttc=1200.0,
        lines_json="[]",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return user_id, org_id, doc


def _pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _vault_row(db, *, org_id: int, vault_id: str, document_type: str = "customer_invoice") -> VaultDocument:
    vault = VaultDocument(
        id=vault_id,
        organization_id=org_id,
        document_type=document_type,
        original_filename="facture.pdf",
        storage_path=f"entreprises/{org_id}/{vault_id}.pdf",
        mime_type="application/pdf",
        file_size=100,
        checksum_sha256=f"checksum-{vault_id}",
        archive_status="archived",
        email_status="pending",
        accounting_status="not_processed",
        currency="EUR",
        version=1,
        archived_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(vault)
    db.commit()
    db.refresh(vault)
    return vault


def _sent_log(doc: SalesDocument, org_id: int, *, key: str = "k1", status: str = "sent") -> DocumentEmailLog:
    return DocumentEmailLog(
        sales_document_id=doc.id,
        organization_id=org_id,
        document_type=doc.doc_type,
        recipient="client@example.com",
        recipient_email="client@example.com",
        subject="Test",
        status=status,
        provider="brevo",
        idempotency_key=key,
        error_code="provider_error" if status == "failed" else "",
        error_message="boom" if status == "failed" else "",
        sent_at=datetime.utcnow(),
    )


def test_attachment_filename():
    doc = SalesDocument(doc_type="facture", number="FACT-2026-0015")
    assert delivery_attachment_filename(doc) == "facture-FACT-2026-0015.pdf"
    doc.doc_type = "devis"
    doc.number = "D-1"
    assert delivery_attachment_filename(doc) == "devis-D-1.pdf"
    doc.doc_type = "avoir"
    doc.number = "A-2"
    assert delivery_attachment_filename(doc) == "avoir-A-2.pdf"


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_invoice_archive_then_send(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db, doc_type="facture")
    vault = _vault_row(db, org_id=org_id, vault_id="vault-1")
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, org_id)

    result = DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="client@example.com",
        subject="Votre facture",
        body="Bonjour",
        idempotency_key="idem-1",
    )
    assert result.status == "sent"
    assert result.email_status == "sent"
    assert result.vault_document_id == "vault-1"
    assert result.vault_archive_status == "archived"
    assert result.reused_existing_archive is False
    mock_archive.assert_called_once()
    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["pdf_bytes"].startswith(b"%PDF")
    assert kwargs["attachment_filename"] == "facture-FACT-2026-0015.pdf"
    assert kwargs["pdf_bytes"] is not None


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_quote_archive_then_send(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db, role_name="owner", doc_type="devis")
    vault = _vault_row(db, org_id=org_id, vault_id="v-quote", document_type="quote")
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, org_id, key="k-quote")
    result = DocumentDeliveryService(db).send_document(
        document_type="devis",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="c@example.com",
        idempotency_key="k-quote",
    )
    assert result.status == "sent"
    assert mock_send.call_args.kwargs["attachment_filename"] == "devis-DEV-2026-0001.pdf"


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_credit_note_archive_then_send(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db, role_name="owner", doc_type="avoir")
    vault = _vault_row(db, org_id=org_id, vault_id="v-cn", document_type="credit_note")
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, org_id, key="k-avoir")
    result = DocumentDeliveryService(db).send_document(
        document_type="avoir",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="c@example.com",
        idempotency_key="k-avoir",
    )
    assert result.status == "sent"
    assert mock_send.call_args.kwargs["attachment_filename"] == "avoir-AV-2026-0001.pdf"


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_reuse_existing_archive(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    vault = _vault_row(db, org_id=org_id, vault_id="reuse-1")
    mock_archive.return_value = (vault, True)
    mock_send.return_value = _sent_log(doc, org_id, key="reuse-key")
    result = DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="c@example.com",
        idempotency_key="reuse-key",
    )
    assert result.reused_existing_archive is True
    assert result.status == "sent"


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf", side_effect=VaultStorageError("down"))
def test_archive_failed_no_mail(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    with pytest.raises(DocumentDeliveryError) as exc:
        DocumentDeliveryService(db).send_document(
            document_type="facture",
            document_id=doc.id,
            organization_id=org_id,
            authenticated_user_id=user_id,
            recipient_email="c@example.com",
        )
    assert exc.value.code == "archive_failed"
    mock_send.assert_not_called()


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_email_failed_keeps_archive(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    vault = _vault_row(db, org_id=org_id, vault_id="fail-1")
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, org_id, key="fail-key", status="failed")
    result = DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="c@example.com",
        idempotency_key="fail-key",
    )
    assert result.status == "email_failed"
    assert result.vault_archive_status == "archived"
    assert result.email_status == "failed"
    still = db.query(VaultDocument).filter(VaultDocument.id == "fail-1").one()
    assert still.archive_status == "archived"
    assert still.email_status == "failed"


def test_cross_tenant_denied():
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    with pytest.raises(DocumentDeliveryError) as exc:
        DocumentDeliveryService(db).send_document(
            document_type="facture",
            document_id=doc.id,
            organization_id=999,
            authenticated_user_id=user_id,
            recipient_email="c@example.com",
        )
    assert exc.value.code == "forbidden"


def test_document_missing():
    db = _session()
    user_id, org_id, _doc = _seed_full(db)
    with pytest.raises(DocumentDeliveryError) as exc:
        DocumentDeliveryService(db).send_document(
            document_type="facture",
            document_id=99999,
            organization_id=org_id,
            authenticated_user_id=user_id,
            recipient_email="c@example.com",
        )
    assert exc.value.code == "not_found"


def test_role_denied_auditeur():
    db = _session()
    user_id, org_id, doc = _seed_full(db, role_name="auditeur")
    with pytest.raises(DocumentDeliveryError) as exc:
        DocumentDeliveryService(db).send_document(
            document_type="facture",
            document_id=doc.id,
            organization_id=org_id,
            authenticated_user_id=user_id,
            recipient_email="c@example.com",
        )
    assert exc.value.code == "forbidden"


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_idempotency_already_sent(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    key = "same-key"
    db.add(_sent_log(doc, org_id, key=key, status="sent"))
    db.commit()
    result = DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="c@example.com",
        idempotency_key=key,
    )
    assert result.already_processed is True
    assert result.status == "already_sent"
    mock_archive.assert_not_called()
    mock_send.assert_not_called()


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_activity_logs_email_sent(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    vault = _vault_row(db, org_id=org_id, vault_id="log-sent")
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, org_id, key="log-sent-key")
    DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="client@example.com",
        idempotency_key="log-sent-key",
    )
    actions = {
        row.action
        for row in db.query(VaultActivityLog).filter(VaultActivityLog.document_id == "log-sent").all()
    }
    assert "email_send_started" in actions
    assert "email_sent" in actions
    for row in db.query(VaultActivityLog).all():
        meta = json.loads(row.metadata_json or "{}")
        assert "pdf" not in json.dumps(meta).lower() or "pdf_bytes" not in meta
        assert "token" not in meta
        assert "service_role" not in json.dumps(meta)
        assert meta.get("recipient_domain") == "example.com"
        assert "client@example.com" not in json.dumps(meta)


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_activity_logs_email_failed(mock_archive, mock_send, _pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    vault = _vault_row(db, org_id=org_id, vault_id="log-fail")
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, org_id, key="log-fail-key", status="failed")
    DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=org_id,
        authenticated_user_id=user_id,
        recipient_email="client@example.com",
        idempotency_key="log-fail-key",
    )
    actions = {
        row.action
        for row in db.query(VaultActivityLog).filter(VaultActivityLog.document_id == "log-fail").all()
    }
    assert "email_failed" in actions


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
def test_idempotency_in_progress(_pdf_mock):
    db = _session()
    user_id, org_id, doc = _seed_full(db)
    key = "busy-key"
    db.add(_sent_log(doc, org_id, key=key, status="preparing"))
    db.commit()
    with pytest.raises(DocumentDeliveryError) as exc:
        DocumentDeliveryService(db).send_document(
            document_type="facture",
            document_id=doc.id,
            organization_id=org_id,
            authenticated_user_id=user_id,
            recipient_email="c@example.com",
            idempotency_key=key,
        )
    assert exc.value.code == "in_progress"
