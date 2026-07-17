from __future__ import annotations

from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models_saas import Organization, SalesDocument
from app.services.billing import create_sales_document
from app.services.email_connections import ensure_platform_connection, upsert_provider_connection
from app.services.sales_email import send_sales_document_email


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_sales_email_records_history_and_from(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.config.settings.email_credentials_encryption_key", key)
    monkeypatch.setattr("app.config.settings.jwt_secret", "test-jwt-secret-for-oauth-state-32c")
    monkeypatch.setattr("app.config.settings.brevo_api_key", "xkeysib-test")
    monkeypatch.setattr("app.config.settings.platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr("app.config.settings.app_env", "development")

    db = _session()
    org = Organization(
        name="IOSTAY",
        legal_name="IOSTAY SAS",
        email="contact@iostay.fr",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    ensure_platform_connection(db, org.id)
    google = upsert_provider_connection(
        db,
        organization_id=org.id,
        provider="google",
        user_id=1,
        email="facturation@iostay.fr",
        display_name="IOSTAY",
        access_token="acc",
        refresh_token="ref",
        expires_in=3600,
        make_default=True,
    )
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Client",
        customer_email="client@email.fr",
        amount_ht=100,
    )

    class FakeResult:
        provider = "google"
        provider_message_id = "msg-42"
        sender_email = "facturation@iostay.fr"
        sender_name = "IOSTAY"

    monkeypatch.setattr(
        "app.services.sales_email.dispatch_email",
        lambda *a, **k: FakeResult(),
    )
    monkeypatch.setattr(
        "app.services.sales_email.sales_document_to_pdf",
        lambda doc, org: b"%PDF-1.4 " + (b"x" * 40),
    )
    monkeypatch.setattr(
        "app.services.sales_email.can_send_document_email",
        lambda *a, **k: (True, ""),
    )

    log = send_sales_document_email(
        db,
        doc,
        recipient="client@email.fr",
        connection_id=google.id,
        sent_by_user_id=1,
        idempotency_key="unique-key-1",
    )
    assert log.status == "sent"
    assert log.provider == "google"
    assert log.sender_email == "facturation@iostay.fr"
    assert log.email_connection_id == google.id
    assert log.provider_message_id == "msg-42"
    assert log.sent_by_user_id == 1

    # Double clic / même clé → pas de second envoi
    log2 = send_sales_document_email(
        db,
        doc,
        recipient="client@email.fr",
        connection_id=google.id,
        sent_by_user_id=1,
        idempotency_key="unique-key-1",
    )
    assert log2.id == log.id
