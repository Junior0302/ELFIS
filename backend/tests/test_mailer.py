from __future__ import annotations

from app.services.mailer import MailAttachment, email_configured, email_transport, send_email


def test_email_not_configured_by_default(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "")
    monkeypatch.setattr(config.settings, "smtp_host", "")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "platform_email_from", "")
    assert email_configured() is False
    assert email_transport() == "none"


def test_brevo_used_when_smtp_incomplete(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")
    assert email_configured() is True
    assert email_transport() == "brevo"


def test_smtp_preferred_when_fully_configured(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "contact@elfis-core.com")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp-relay.brevo.com")
    monkeypatch.setattr(config.settings, "smtp_user", "8dc723001@smtp-brevo.com")
    monkeypatch.setattr(config.settings, "smtp_password", "xsmtpsib-test-key")
    assert email_configured() is True
    assert email_transport() == "smtp"


def test_send_email_via_brevo_uses_org_identity(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-test")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "ComptaPilot")

    calls: list[dict] = []

    class FakeResponse:
        status_code = 201
        text = '{"messageId":"<msg-1@brevo>"}'

        def json(self):
            return {"messageId": "<msg-1@brevo>"}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.services.mailer.httpx.post", fake_post)
    result = send_email(
        to_email="client@exemple.fr",
        subject="Facture FAC-1 — IOSTAY",
        body="Bonjour",
        attachments=[MailAttachment(filename="Facture-FAC-1-IOSTAY.pdf", content=b"%PDF-1.4", subtype="pdf")],
        sender_name="IOSTAY",
        reply_to_email="contact@iostay.fr",
        reply_to_name="IOSTAY",
    )
    assert result.provider == "brevo"
    assert result.provider_message_id == "<msg-1@brevo>"
    payload = calls[0]["json"]
    assert payload["sender"]["email"] == "documents@elfiscore.com"
    assert payload["sender"]["name"] == "IOSTAY"
    assert payload["replyTo"]["email"] == "contact@iostay.fr"
    assert payload["attachment"][0]["name"] == "Facture-FAC-1-IOSTAY.pdf"
