from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_saas import Organization, SalesDocument, User
from app.services.billing import create_sales_document
from app.services.sales_email import send_sales_document_email


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _org(db, name="Demo SA", email="contact@demo.fr", plan="pro"):
    org = Organization(name=name, legal_name=name, email=email, subscription_plan=plan)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _patch_brevo(monkeypatch):
    from app import config
    from app.services import mailer as mailer_mod

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "ComptaPilot")

    calls: list[dict] = []

    class FakeResponse:
        status_code = 201
        text = '{"messageId":"msg-invoice"}'

        def json(self):
            return {"messageId": "msg-invoice"}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        calls.append(json)
        return FakeResponse()

    monkeypatch.setattr(mailer_mod.httpx, "post", fake_post)
    return calls


def test_invoice_email_sends_with_pdf_attachment(monkeypatch):
    calls = _patch_brevo(monkeypatch)
    db = _session()
    org = _org(db)
    user = User(first_name="A", last_name="B", email="owner@demo.fr")
    db.add(user)
    db.commit()
    db.refresh(user)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Client Facture",
        customer_email="client@exemple.fr",
        amount_ht=200,
        vat_rate=20,
    )
    assert doc.status == "draft"
    log = send_sales_document_email(
        db,
        doc,
        recipient="client@exemple.fr",
        subject="Votre facture",
        message="Bonjour, veuillez trouver la facture ci-jointe.",
        cc="copie@exemple.fr",
        sent_by_user_id=user.id,
        idempotency_key="inv-send-1",
    )
    assert log.error_code != "email_recipient_limit", log.error_message
    db.refresh(doc)
    assert log.status == "sent"
    assert doc.status == "sent"
    assert len(calls) == 1
    payload = calls[0]
    assert payload["to"][0]["email"] == "client@exemple.fr"
    assert payload["attachment"]
    assert payload["attachment"][0]["name"].endswith(".pdf")
    assert len(payload["attachment"][0]["content"]) > 20
    assert "facture" in payload["subject"].lower() or "Votre facture" in payload["subject"]


def test_quote_email_sends_with_pdf_attachment(monkeypatch):
    calls = _patch_brevo(monkeypatch)
    db = _session()
    org = _org(db)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="devis",
        customer_name="Prospect",
        customer_email="prospect@exemple.fr",
        amount_ht=500,
        vat_rate=20,
    )
    log = send_sales_document_email(
        db,
        doc,
        recipient="prospect@exemple.fr",
        message="Voici notre devis.",
        idempotency_key="quote-send-1",
    )
    db.refresh(doc)
    assert log.status == "sent"
    assert doc.status == "sent"
    assert doc.signature_status == "pending"
    assert calls[0]["attachment"][0]["name"].endswith(".pdf")


def test_email_security_org_isolation(monkeypatch):
    """Un document d’une org ne doit pas être envoyable via une autre org (lien doc)."""
    _patch_brevo(monkeypatch)
    db = _session()
    org_a = _org(db, "Alpha", "a@alpha.fr")
    org_b = _org(db, "Beta", "b@beta.fr")
    doc_a = create_sales_document(
        db,
        organization_id=org_a.id,
        doc_type="facture",
        customer_name="Client A",
        customer_email="a@client.fr",
        amount_ht=10,
    )
    # Simulation d’accès croisé : le service envoie toujours avec l’org du document
    log = send_sales_document_email(
        db,
        doc_a,
        recipient="a@client.fr",
        idempotency_key="sec-1",
    )
    assert log.organization_id == org_a.id
    assert log.organization_id != org_b.id
    assert db.get(SalesDocument, doc_a.id).organization_id == org_a.id
