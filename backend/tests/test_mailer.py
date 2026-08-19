from __future__ import annotations

from app.services.mailer import MailAttachment, email_configured, email_transport, mailer_reason_code, send_email


def test_email_not_configured_by_default(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "")
    monkeypatch.setattr(config.settings, "smtp_host", "")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "platform_email_from", "")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")
    assert email_configured() is False
    assert email_transport() == "none"
    assert mailer_reason_code() == "sender_not_configured"


def test_brevo_used_when_smtp_incomplete(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")
    assert email_configured() is True
    assert email_transport() == "brevo"
    assert mailer_reason_code() == "ok"


def test_brevo_api_preferred_when_both_configured(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "contact@elfis-core.com")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp-relay.brevo.com")
    monkeypatch.setattr(config.settings, "smtp_user", "8dc723001@smtp-brevo.com")
    monkeypatch.setattr(config.settings, "smtp_password", "xsmtpsib-test-key")
    assert email_configured() is True
    assert email_transport() == "brevo"
    assert mailer_reason_code() == "ok"


def test_send_email_prefers_brevo_api_over_smtp(monkeypatch):
    """Quand API + SMTP sont prêts, httpx Brevo est appelé — pas smtplib."""
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "contact@elfis-core.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "ComptaPilot")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp-relay.brevo.com")
    monkeypatch.setattr(config.settings, "smtp_user", "user@smtp-brevo.com")
    monkeypatch.setattr(config.settings, "smtp_password", "xsmtpsib-test-key")

    calls: list[dict] = []

    class FakeResponse:
        status_code = 201
        text = '{"messageId":"<api-first@brevo>"}'

        def json(self):
            return {"messageId": "<api-first@brevo>"}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        calls.append({"url": url, "headers": headers or {}, "json": json})
        return FakeResponse()

    def boom_smtp(*_a, **_k):
        raise AssertionError("SMTP ne doit pas être appelé quand l’API Brevo réussit")

    monkeypatch.setattr("app.services.mailer.httpx.post", fake_post)
    monkeypatch.setattr("app.services.mailer._send_via_smtp", boom_smtp)

    result = send_email(
        to_email="validation@test.elfis.local",
        subject="Test priorité API",
        body="corps",
        attachments=[MailAttachment(filename="test.pdf", content=b"%PDF-1.4", subtype="pdf")],
    )
    assert result.provider == "brevo"
    assert result.provider_message_id == "<api-first@brevo>"
    assert calls[0]["url"] == "https://api.brevo.com/v3/smtp/email"
    assert "api-key" in calls[0]["headers"]
    # Jamais la clé complète dans les assertions / logs de test
    assert calls[0]["headers"]["api-key"].startswith("xkeysib-")
    assert calls[0]["json"]["sender"]["email"] == "contact@elfis-core.com"
    assert calls[0]["json"]["attachment"][0]["name"] == "test.pdf"


def test_missing_smtp_credentials_reason(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp-relay.brevo.com")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")
    assert email_configured() is False
    assert mailer_reason_code() == "missing_smtp_credentials"


def test_send_email_via_brevo_uses_org_identity(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "ComptaPilot")
    monkeypatch.setattr(config.settings, "smtp_host", "")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")

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

