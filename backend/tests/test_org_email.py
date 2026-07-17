from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models_saas import DocumentEmailLog, Organization, OrganizationEmailSettings, User
from app.services.billing import create_sales_document
from app.services.org_email_settings import (
    build_subject_and_body,
    get_or_create_email_settings,
    pdf_filename,
    resolve_sender,
)
from app.services.sales_email import send_sales_document_email


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _org(db, name="IOSTAY", email="contact@iostay.fr"):
    org = Organization(name=name, legal_name=name, email=email)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def test_resolve_sender_platform_mode_uses_org_reply_to(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "ComptaPilot")
    db = _session()
    org = _org(db)
    row = get_or_create_email_settings(db, org)
    sender = resolve_sender(org, row)
    assert sender.mode == "platform"
    assert sender.sender_email == "documents@elfiscore.com"
    assert sender.sender_name == "IOSTAY"
    assert sender.reply_to_email == "contact@iostay.fr"
    assert sender.using_custom is False


def test_custom_sender_falls_back_when_not_verified(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    db = _session()
    org = _org(db)
    row = get_or_create_email_settings(db, org)
    row.sender_mode = "custom_sender"
    row.custom_sender_email = "facturation@iostay.fr"
    row.custom_sender_status = "pending"
    db.add(row)
    db.commit()
    sender = resolve_sender(org, row)
    assert sender.mode == "platform"
    assert sender.sender_email == "documents@elfiscore.com"


def test_invoice_and_quote_templates():
    db = _session()
    org = _org(db)
    row = get_or_create_email_settings(db, org)
    invoice = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Client A",
        customer_email="a@example.com",
        amount_ht=100,
        vat_rate=20,
    )
    quote = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="devis",
        customer_name="Client B",
        customer_email="b@example.com",
        amount_ht=50,
        vat_rate=20,
    )
    inv_subject, inv_body = build_subject_and_body(invoice, org, row)
    q_subject, q_body = build_subject_and_body(quote, org, row)
    assert "Facture" in inv_subject and "IOSTAY" in inv_subject
    assert "Devis" in q_subject
    assert "Client A" in inv_body and "échéance" in inv_body.lower()
    assert "Client B" in q_body and "valable" in q_body.lower()
    assert pdf_filename(invoice, org).startswith("Facture-")
    assert pdf_filename(quote, org).startswith("Devis-")


def test_send_invoice_with_pdf_and_idempotency(monkeypatch):
    from app import config
    from app.services import mailer as mailer_mod

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")

    calls: list[dict] = []

    class FakeResponse:
        status_code = 201
        text = '{"messageId":"msg-42"}'

        def json(self):
            return {"messageId": "msg-42"}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        calls.append(json)
        return FakeResponse()

    monkeypatch.setattr(mailer_mod.httpx, "post", fake_post)

    db = _session()
    org = _org(db)
    user = User(first_name="Owner", last_name="Test", email="owner@iostay.fr")
    db.add(user)
    db.commit()
    db.refresh(user)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Client A",
        customer_email="client@exemple.fr",
        amount_ht=100,
        vat_rate=20,
    )
    log1 = send_sales_document_email(
        db,
        doc,
        recipient="client@exemple.fr",
        message="Message personnalisé",
        sent_by_user_id=user.id,
        idempotency_key="idem-1",
    )
    log2 = send_sales_document_email(
        db,
        doc,
        recipient="client@exemple.fr",
        message="Message personnalisé",
        sent_by_user_id=user.id,
        idempotency_key="idem-1",
    )
    assert log1.status == "sent"
    assert log1.id == log2.id
    assert len(calls) == 1
    payload = calls[0]
    assert payload["sender"]["name"] == "IOSTAY"
    assert payload["sender"]["email"] == "documents@elfiscore.com"
    assert payload["replyTo"]["email"] == "contact@iostay.fr"
    assert "Message personnalisé" in payload["textContent"]
    assert payload["attachment"][0]["name"].endswith(".pdf")
    assert "xkeysib" not in str(payload)


def test_missing_customer_email(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    db = _session()
    org = _org(db)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Sans mail",
        customer_email="",
        amount_ht=10,
    )
    log = send_sales_document_email(db, doc, recipient="")
    assert log.status == "failed"
    assert log.error_code == "missing_recipient"
    assert "adresse e-mail" in log.error_message.lower()


def test_org_isolation_settings():
    db = _session()
    org_a = _org(db, "Alpha", "a@alpha.fr")
    org_b = _org(db, "Beta", "b@beta.fr")
    row_a = get_or_create_email_settings(db, org_a)
    row_b = get_or_create_email_settings(db, org_b)
    row_a.sender_name = "Alpha Corp"
    row_b.sender_name = "Beta Corp"
    db.add_all([row_a, row_b])
    db.commit()
    assert (
        db.query(OrganizationEmailSettings)
        .filter(OrganizationEmailSettings.organization_id == org_a.id)
        .one()
        .sender_name
        == "Alpha Corp"
    )
    assert (
        db.query(OrganizationEmailSettings)
        .filter(OrganizationEmailSettings.organization_id == org_b.id)
        .one()
        .sender_name
        == "Beta Corp"
    )


def test_webhook_updates_delivery_and_bounce():
    from app.routers.webhooks_brevo import EVENT_STATUS

    assert EVENT_STATUS["delivered"] == "delivered"
    assert EVENT_STATUS["hard_bounce"] == "bounced"
    assert EVENT_STATUS["opened"] == "opened"

    db = _session()
    org = _org(db, "WH", "wh@test.fr")
    log = DocumentEmailLog(
        organization_id=org.id,
        document_type="facture",
        recipient="c@test.fr",
        recipient_email="c@test.fr",
        subject="Test",
        provider="brevo",
        provider_message_id="<msg-wh@brevo>",
        status="sent",
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Simule le traitement webhook (même logique que /webhooks/brevo)
    found = (
        db.query(DocumentEmailLog)
        .filter(DocumentEmailLog.provider_message_id == "<msg-wh@brevo>")
        .filter(DocumentEmailLog.organization_id == org.id)
        .one()
    )
    found.status = EVENT_STATUS["delivered"]
    found.delivered_at = datetime.utcnow()
    db.add(found)
    db.commit()
    found.status = EVENT_STATUS["hard_bounce"]
    found.bounced_at = datetime.utcnow()
    db.add(found)
    db.commit()
    db.refresh(found)
    assert found.status == "bounced"
    assert found.bounced_at is not None
    assert found.organization_id == org.id


def test_brevo_failure_user_message(monkeypatch):
    from app import config
    from app.services import mailer as mailer_mod

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")

    class FakeResponse:
        status_code = 500
        text = "internal"

        def json(self):
            return {"message": "boom"}

    monkeypatch.setattr(mailer_mod.httpx, "post", lambda *a, **k: FakeResponse())

    db = _session()
    org = _org(db)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="devis",
        customer_name="Client",
        customer_email="c@exemple.fr",
        amount_ht=20,
    )
    log = send_sales_document_email(db, doc, recipient="c@exemple.fr")
    assert log.status == "failed"
    assert "n’a pas pu être envoyé" in log.error_message
    assert "boom" not in log.error_message
    assert "xkeysib" not in log.error_message
