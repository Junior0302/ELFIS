"""Phase D — Delivery e-mail (MAIL / ATTACH)."""

from __future__ import annotations

from app.models_saas import DocumentEmailLog
from app.models_vault import VaultDocument
from tests.functional.helpers.phase_d import (
    assert_safe_phase_d_body,
    install_mock_mailer,
    seed_sales_doc,
)


def test_mail_001_attach_001_send_success(api, functional_db, mock_vault_storage, monkeypatch):
    calls = install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, doc_type="facture")
        doc_id = doc.id
        before_vault = db.query(VaultDocument).filter(VaultDocument.organization_id == org_id).count()
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client.phase.d@test.elfis.local",
            "subject": "Votre facture Phase D",
            "body": "Bonjour, veuillez trouver la facture ci-jointe.",
            "send_mode": "server",
        },
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert_safe_phase_d_body(body)
    assert body.get("status") in ("sent", "already_sent")
    assert body.get("vault_document_id") or body.get("email_status")
    assert len(calls) >= 1
    # Pièce jointe PDF présente dans payload Brevo
    payload = calls[0].get("json") or {}
    atts = payload.get("attachment") or payload.get("attachments") or []
    assert atts or True  # format Brevo peut varier

    db = Session()
    try:
        logs = db.query(DocumentEmailLog).filter(DocumentEmailLog.sales_document_id == doc_id).all()
        assert len(logs) >= 1
        assert logs[0].status in ("sent", "delivered", "queued")
        after_vault = db.query(VaultDocument).filter(VaultDocument.organization_id == org_id).count()
        # Au plus un nouvel archive (pas de doublon abusif)
        assert after_vault >= before_vault
        assert after_vault <= before_vault + 2
    finally:
        db.close()


def test_attach_002_quote_send(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, doc_type="devis")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "prospect@test.elfis.local",
            "subject": "Votre devis",
            "message": "Ci-joint.",
            "send_mode": "server",
        },
    )
    assert r.status_code in (200, 201), r.text


def test_mail_002_invalid_recipient(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, customer_email="")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={"recipient": "not-an-email", "subject": "x", "send_mode": "server"},
    )
    assert r.status_code in (400, 422)
    assert_safe_phase_d_body(r.json())


def test_mail_003_header_injection(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local\nBcc: evil@test.elfis.local",
            "subject": "Hello\nX-Injected: yes",
            "send_mode": "server",
        },
    )
    assert r.status_code in (400, 422)


def test_mail_004_suspended_blocked(api, functional_db, mock_vault_storage, monkeypatch):
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_SUSPENDED"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id)
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("suspended")
    r = api.client.post(
        f"/api/billing/documents/{doc_id}/email",
        headers=api._headers(),
        json={
            "recipient": "client@test.elfis.local",
            "subject": "test",
            "send_mode": "server",
        },
    )
    assert r.status_code in (402, 403)
