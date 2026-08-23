"""A1.1.6 — validation chaîne delivery (mocks mailer/Vault, pas d'envoi réel)."""

from __future__ import annotations

import logging

from app.models_saas import DocumentEmailLog
from app.models_vault import VaultDocument
from tests.functional.helpers.phase_d import install_mock_mailer, seed_sales_doc


def test_a116_delivery_steps_logged_and_status_sent(
    api, functional_db, mock_vault_storage, monkeypatch, caplog
):
    """PDF → Vault → e-mail mock : steps tracés, historique, email_status=sent."""
    install_mock_mailer(monkeypatch)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        doc = seed_sales_doc(db, org_id=org_id, doc_type="facture")
        doc_id = doc.id
    finally:
        db.close()

    api.login_user("org_admin")
    with caplog.at_level(logging.INFO):
        r = api.client.post(
            f"/api/billing/documents/{doc_id}/email",
            headers=api._headers(),
            json={
                "recipient": "validation.a116@test.elfis.local",
                "subject": "Votre facture A1.1.6",
                "body": "Bonjour, facture de test en pièce jointe.",
                "send_mode": "server",
                "is_test": True,
            },
        )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body.get("status") in ("sent", "already_sent")
    assert body.get("email_status") in ("sent", None) or body.get("status") == "already_sent"

    messages = [rec.getMessage() for rec in caplog.records]
    assert any("document_delivery_step:PDF_CREATED" in m for m in messages)
    assert any("document_delivery_step:VAULT_UPLOAD_SUCCESS" in m for m in messages)
    assert any("document_delivery_step:EMAIL_SENT" in m for m in messages)
    assert any("document_delivery_step:EMAIL_CONFIRMED" in m for m in messages)
    # Pas de fuite évidente de secrets dans les messages de step
    joined = "\n".join(messages)
    assert "xsmtpsib-" not in joined
    assert "service_role" not in joined.lower() or "mock-service-role" in joined

    db = Session()
    try:
        logs = (
            db.query(DocumentEmailLog)
            .filter(DocumentEmailLog.sales_document_id == doc_id)
            .order_by(DocumentEmailLog.id.desc())
            .all()
        )
        assert logs
        assert logs[0].status in ("sent", "delivered", "queued")
        assert "facture" in (logs[0].subject or "").lower() or "A1.1.6" in (logs[0].subject or "")
        vault_id = body.get("vault_document_id")
        if vault_id:
            vault = db.get(VaultDocument, vault_id)
            assert vault is not None
            assert vault.email_status == "sent"
            assert vault.checksum_sha256
    finally:
        db.close()


def test_smtp_auth_failure_message_is_explicit():
    """Auth SMTP 535 → code normalisé, sans secret ni message flou."""
    from app.services.email_providers.types import EmailProviderError
    from app.services.mailer import _send_via_smtp
    import smtplib
    from unittest.mock import MagicMock, patch

    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    smtp.__exit__.return_value = False
    smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")

    with patch("app.services.email_providers.platform.smtplib.SMTP", return_value=smtp):
        with patch("app.services.email_providers.platform.settings") as settings:
            settings.smtp_host = "smtp-relay.brevo.com"
            settings.smtp_port = 587
            settings.smtp_use_tls = True
            settings.smtp_user = "user@smtp-brevo.com"
            settings.smtp_password = "xsmtpsib-test"
            settings._clean_secret = lambda v: (v or "").strip()
            try:
                _send_via_smtp(
                    to_email="validation@example.com",
                    subject="x",
                    body="y",
                    attachments=[],
                    from_email="contact@elfis-core.com",
                    from_name="ELFIS Core",
                    reply_to_email=None,
                    cc=[],
                    bcc=[],
                )
                raised = None
            except EmailProviderError as exc:
                raised = exc
    assert raised is not None
    assert raised.error_code == "authentication_failed"
    assert raised.smtp_code == "535"
    msg = str(raised)
    assert "Service temporairement indisponible" not in msg
    assert "xsmtpsib-test" not in msg
    assert "xkeysib-" not in msg
