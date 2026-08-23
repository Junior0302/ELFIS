from __future__ import annotations

import smtplib

import pytest

from app.services.email_providers.platform import PlatformEmailProvider
from app.services.email_providers.types import (
    DEFAULT_SENDER_NAME,
    EmailProviderError,
    user_safe_message,
)
from app.services.mailer import MailAttachment, send_email
from app.services.sales_email import _user_facing_error


def _ready_both(monkeypatch) -> None:
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp-relay.brevo.com")
    monkeypatch.setattr(config.settings, "smtp_user", "user@smtp-brevo.com")
    monkeypatch.setattr(config.settings, "smtp_password", "xsmtpsib-test-key")


def _ready_api_only(monkeypatch) -> None:
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "smtp_host", "")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or "{}"

    def json(self):
        return self._payload


def test_brevo_api_success_returns_message_id(monkeypatch):
    _ready_api_only(monkeypatch)
    calls: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse(201, {"messageId": "<msg-api@brevo>"})

    result = PlatformEmailProvider(http_post=fake_post).send(
        to_email="client@exemple.fr",
        subject="Facture",
        body="Bonjour",
        attachments=[MailAttachment(filename="facture-1.pdf", content=b"%PDF-1.4", subtype="pdf")],
        reply_to_email="contact@entreprise.fr",
        reply_to_name="Entreprise",
    )
    assert result.success is True
    assert result.provider == "platform"
    assert result.transport == "brevo_api"
    assert result.provider_message_id == "<msg-api@brevo>"
    assert result.used_fallback is False
    payload = calls[0]["json"]
    assert payload["sender"]["email"] == "documents@elfiscore.com"
    assert payload["replyTo"]["email"] == "contact@entreprise.fr"
    assert payload["attachment"][0]["name"] == "facture-1.pdf"
    assert payload["attachment"][0]["content"]
    assert "xkeysib-" not in str(result)


def test_brevo_api_success_never_calls_smtp(monkeypatch):
    _ready_both(monkeypatch)

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(201, {"messageId": "<ok@brevo>"})

    def boom_smtp(**_kwargs):
        raise AssertionError("SMTP ne doit pas être appelé quand l’API réussit")

    result = PlatformEmailProvider(http_post=fake_post, smtp_send=boom_smtp).send(
        to_email="client@exemple.fr",
        subject="x",
        body="y",
    )
    assert result.transport == "brevo_api"
    assert result.used_fallback is False


def test_brevo_api_auth_failure_falls_back_to_smtp_success(monkeypatch):
    _ready_both(monkeypatch)
    smtp_calls: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(401, {"message": "Key not found"})

    def fake_smtp(**kwargs):
        smtp_calls.append(kwargs)

    result = PlatformEmailProvider(http_post=fake_post, smtp_send=fake_smtp).send(
        to_email="client@exemple.fr",
        subject="x",
        body="y",
        attachments=[MailAttachment(filename="doc.pdf", content=b"%PDF-1.4")],
        reply_to_email="reponse@entreprise.fr",
    )
    assert result.success is True
    assert result.transport == "smtp"
    assert result.used_fallback is True
    assert smtp_calls[0]["reply_to_email"] == "reponse@entreprise.fr"
    assert smtp_calls[0]["attachments"][0].filename == "doc.pdf"


def test_api_and_smtp_auth_failure_prefers_api_code(monkeypatch):
    _ready_both(monkeypatch)

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(401, {"message": "Key not found"})

    def fail_smtp(**_kwargs):
        raise EmailProviderError("authentication_failed", transport="smtp", smtp_code="535")

    with pytest.raises(EmailProviderError) as exc:
        PlatformEmailProvider(http_post=fake_post, smtp_send=fail_smtp).send(
            to_email="client@exemple.fr",
            subject="x",
            body="y",
        )
    assert exc.value.error_code == "authentication_failed"
    assert exc.value.used_fallback is True
    assert "xkeysib-" not in str(exc.value)
    assert "xsmtpsib" not in str(exc.value)
    assert "535" not in str(exc.value)


def test_temporary_api_failure_falls_back(monkeypatch):
    _ready_both(monkeypatch)

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(503, {"message": "unavailable"})

    def fake_smtp(**_kwargs):
        return None

    result = PlatformEmailProvider(http_post=fake_post, smtp_send=fake_smtp).send(
        to_email="client@exemple.fr",
        subject="x",
        body="y",
    )
    assert result.success is True
    assert result.used_fallback is True
    assert result.transport == "smtp"


def test_recipient_invalid_does_not_fallback(monkeypatch):
    _ready_both(monkeypatch)

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(400, {"message": "invalid email recipient"})

    def boom_smtp(**_kwargs):
        raise AssertionError("pas de fallback SMTP sur destinataire invalide")

    with pytest.raises(EmailProviderError) as exc:
        PlatformEmailProvider(http_post=fake_post, smtp_send=boom_smtp).send(
            to_email="client@exemple.fr",
            subject="x",
            body="y",
        )
    assert exc.value.error_code == "recipient_invalid"
    assert exc.value.used_fallback is False


def test_provider_not_configured(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "")
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "smtp_host", "")
    monkeypatch.setattr(config.settings, "smtp_user", "")
    monkeypatch.setattr(config.settings, "smtp_password", "")
    with pytest.raises(EmailProviderError) as exc:
        PlatformEmailProvider().send(to_email="a@b.fr", subject="x", body="y")
    assert exc.value.error_code == "provider_not_configured"


def test_from_absent(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "")
    monkeypatch.setattr(config.settings, "smtp_from", "")
    monkeypatch.setattr(config.settings, "smtp_host", "smtp-relay.brevo.com")
    monkeypatch.setattr(config.settings, "smtp_user", "user@smtp-brevo.com")
    monkeypatch.setattr(config.settings, "smtp_password", "xsmtpsib-test-key")
    with pytest.raises(EmailProviderError) as exc:
        PlatformEmailProvider().send(to_email="a@b.fr", subject="x", body="y")
    assert exc.value.error_code == "sender_not_configured"


def test_default_sender_name_is_elfis_core(monkeypatch):
    _ready_api_only(monkeypatch)
    from app import config

    monkeypatch.setattr(config.settings, "platform_email_from_name", "")

    captured: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        captured.append(json)
        return _FakeResponse(201, {"messageId": "1"})

    PlatformEmailProvider(http_post=fake_post).send(
        to_email="a@b.fr",
        subject="x",
        body="y",
    )
    assert captured[0]["sender"]["name"] == DEFAULT_SENDER_NAME
    assert captured[0]["sender"]["name"] != "ComptaPilot"


def test_send_email_facade_maps_transport(monkeypatch):
    _ready_api_only(monkeypatch)

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(201, {"messageId": "<facade@brevo>"})

    monkeypatch.setattr("app.services.mailer.httpx.post", fake_post)
    result = send_email(to_email="a@b.fr", subject="x", body="y")
    assert result.provider == "brevo"
    assert result.transport == "brevo_api"
    assert result.provider_message_id == "<facade@brevo>"


def test_user_facing_error_hides_provider_internals():
    exc = EmailProviderError(
        "authentication_failed",
        transport="brevo_api",
        http_status=401,
        smtp_code="535",
    )
    code, message = _user_facing_error(exc)
    assert code == "authentication_failed"
    assert message == user_safe_message("authentication_failed")
    assert "535" not in message
    assert "401" not in message
    assert "brevo" not in message.lower()
    assert "xkeysib" not in message


def test_health_without_network_has_no_secrets(monkeypatch):
    _ready_both(monkeypatch)
    snapshot = PlatformEmailProvider().health(live=False)
    dumped = str(snapshot)
    assert "xkeysib-" not in dumped
    assert "xsmtpsib" not in dumped
    assert snapshot["preferred_transport"] == "brevo_api"
    assert snapshot["fallback_available"] is True
    assert snapshot["platform_from_configured"] is True
    assert snapshot["brevo_api"]["configured"] is True
    assert snapshot["brevo_api"]["format_usable"] is True
    assert snapshot["smtp"]["configured"] is True
    assert snapshot["brevo_api"]["auth"] == "skipped"


def test_live_health_reports_api_and_smtp_separately(monkeypatch):
    _ready_both(monkeypatch)

    def fake_get(url, headers=None, timeout=None):  # noqa: ANN001
        return _FakeResponse(401, {"message": "Key not found"})

    monkeypatch.setattr(
        "app.services.email_providers.platform.probe_smtp_login",
        lambda: {"connect": "ok", "auth": "failed", "error": "authentication_failed"},
    )
    snapshot = PlatformEmailProvider(http_get=fake_get).health(live=True)
    assert snapshot["brevo_api"]["auth"] == "failed"
    assert snapshot["brevo_api"]["http_status"] == 401
    assert snapshot["smtp"]["auth"] == "failed"
    assert snapshot["reason_code"] == "authentication_failed"
    assert "xkeysib-" not in str(snapshot)
