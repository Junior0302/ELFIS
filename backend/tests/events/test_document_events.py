"""Tests publication d'événements depuis DocumentDeliveryService."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models_saas import DocumentEmailLog, Organization, OrganizationMember, Role, SalesDocument, User
from app.models_vault import VaultDocument
from app.services.document_delivery import DocumentDeliveryService


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db, *, doc_type: str = "facture"):
    db.add(Organization(id=1, name="Org", currency="EUR", email="org@example.com"))
    role = Role(id=1, name="owner", permissions='["documents.send_email"]')
    db.add(role)
    db.add(User(id=1, first_name="A", last_name="B", email="u@example.com", status="active"))
    db.add(OrganizationMember(user_id=1, organization_id=1, role_id=1, status="active"))
    doc = SalesDocument(
        organization_id=1,
        doc_type=doc_type,
        number="FACT-1",
        issue_date="2026-07-20",
        due_date="2026-08-20",
        status="draft",
        customer_name="Client",
        customer_email="client@example.com",
        amount_ht=100.0,
        amount_tva=20.0,
        amount_ttc=120.0,
        lines_json="[]",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _vault(db, vault_id: str = "vault-evt-1") -> VaultDocument:
    vault = VaultDocument(
        id=vault_id,
        organization_id=1,
        document_type="customer_invoice",
        original_filename="f.pdf",
        storage_path="p.pdf",
        mime_type="application/pdf",
        file_size=10,
        checksum_sha256="abc",
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


def _pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _sent_log(doc, *, status: str = "sent") -> DocumentEmailLog:
    return DocumentEmailLog(
        sales_document_id=doc.id,
        organization_id=1,
        document_type=doc.doc_type,
        recipient="client@example.com",
        recipient_email="client@example.com",
        subject="s",
        status=status,
        provider="brevo",
        idempotency_key="k",
        error_code="provider_error" if status == "failed" else "",
        sent_at=datetime.utcnow(),
    )


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_delivery_publishes_archived_started_sent(mock_archive, mock_send, _pdf_mock):
    db = _session()
    doc = _seed(db)
    vault = _vault(db)
    mock_archive.return_value = (vault, False)
    mock_send.return_value = _sent_log(doc, status="sent")

    DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=1,
        authenticated_user_id=1,
        recipient_email="client@example.com",
        idempotency_key="evt-send-1",
    )
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.VAULT_DOCUMENT_ARCHIVED in names
    assert EventNames.DELIVERY_EMAIL_STARTED in names
    assert EventNames.DELIVERY_EMAIL_SENT in names
    archived = db.query(ElfisEvent).filter(ElfisEvent.event_name == EventNames.VAULT_DOCUMENT_ARCHIVED).one()
    assert archived.correlation_id
    assert "pdf" not in str(archived.payload).lower() or "pdf_bytes" not in archived.payload
    assert "pdf_bytes" not in archived.payload
    assert archived.organization_id == 1
    # correlation partagée
    corrs = {e.correlation_id for e in db.query(ElfisEvent).all()}
    assert len(corrs) == 1


@patch("app.services.document_delivery.sales_document_to_pdf", return_value=_pdf())
@patch("app.services.document_delivery.send_sales_document_email")
@patch("app.services.document_delivery.archive_or_reuse_pdf")
def test_delivery_publishes_reused_and_failed(mock_archive, mock_send, _pdf_mock):
    db = _session()
    doc = _seed(db)
    vault = _vault(db, "vault-reuse")
    mock_archive.return_value = (vault, True)
    mock_send.return_value = _sent_log(doc, status="failed")

    DocumentDeliveryService(db).send_document(
        document_type="facture",
        document_id=doc.id,
        organization_id=1,
        authenticated_user_id=1,
        recipient_email="client@example.com",
        idempotency_key="evt-fail-1",
    )
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.VAULT_DOCUMENT_REUSED in names
    assert EventNames.DELIVERY_EMAIL_STARTED in names
    assert EventNames.DELIVERY_EMAIL_FAILED in names
    assert EventNames.VAULT_DOCUMENT_ARCHIVED not in names
    failed = db.query(ElfisEvent).filter(ElfisEvent.event_name == EventNames.DELIVERY_EMAIL_FAILED).one()
    assert failed.payload.get("error_code") == "provider_error"
    assert "api_key" not in failed.payload
