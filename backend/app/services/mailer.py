from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.services.email_providers.platform import (
    PlatformEmailProvider,
    brevo_api_ready,
    preferred_transport,
    probe_smtp_login,
    send_via_brevo_api,
    send_via_platform_smtp,
    smtp_ready,
    _config_reason_code,
    _brevo_api_key,
)
from app.services.email_providers.types import ProviderSendResult
from app.services.mailer_types import MailAttachment

# httpx reste importé ici pour que les tests existants patchent app.services.mailer.httpx.post
import httpx

__all__ = [
    "MailAttachment",
    "SendEmailResult",
    "email_configured",
    "email_status_public",
    "email_transport",
    "mailer_diagnostic",
    "mailer_reason_code",
    "probe_brevo_account",
    "send_email",
]


@dataclass(frozen=True)
class SendEmailResult:
    provider: str
    provider_message_id: str = ""
    sender_email: str = ""
    sender_name: str = ""
    transport: str = ""
    used_fallback: bool = False


def _smtp_ready() -> bool:
    return smtp_ready()


def _brevo_api_key_usable() -> bool:
    return brevo_api_ready()


def _smtp_user_public() -> dict:
    """Infos non secrètes sur SMTP_USER pour le diagnostic admin existant."""
    user = settings.smtp_user.strip()
    password = settings.smtp_password.strip()
    looks_brevo_login = user.lower().endswith("@smtp-brevo.com")
    masked = ""
    if user:
        if "@" in user:
            local, _, domain = user.partition("@")
            keep = local[:3] if len(local) > 3 else local[:1]
            masked = f"{keep}…@{domain}"
        else:
            masked = f"{user[:3]}…" if len(user) > 3 else "***"
    return {
        "smtp_user_masked": masked,
        "smtp_user_looks_brevo": looks_brevo_login,
        "smtp_password_looks_brevo": password.startswith("xsmtpsib-") and len(password) > 20,
        "smtp_password_length": len(password),
        "smtp_host_value": settings.smtp_host.strip(),
        "smtp_port_value": settings.smtp_port,
    }


def _probe_smtp_login() -> tuple[bool, str]:
    probed = probe_smtp_login()
    if probed.get("auth") == "ok" and probed.get("connect") == "ok":
        return True, ""
    if probed.get("error") == "authentication_failed":
        return False, "authentication_failed"
    if probed.get("error") == "not_configured":
        return False, "SMTP incomplet : SMTP_HOST, SMTP_USER et SMTP_PASSWORD requis."
    return False, probed.get("error") or "provider_unreachable"


def email_configured() -> bool:
    """True si SMTP plateforme ou API Brevo est prêt (clés plateforme uniquement)."""
    return smtp_ready() or brevo_api_ready()


def email_transport() -> str:
    # Compat : "brevo" | "smtp" | "none" — le transport interne est brevo_api | smtp.
    mapping = {"brevo_api": "brevo", "smtp": "smtp", "none": "none"}
    return mapping.get(preferred_transport(), "none")


def mailer_reason_code() -> str:
    """Code machine stable pour UI / health (jamais de secret)."""
    return _config_reason_code()


def mailer_diagnostic() -> dict:
    """Diagnostic admin/dev sécurisé — pas de secrets en clair."""
    transport = email_transport()
    provider = {
        "smtp": "smtp",
        "brevo": "brevo_api",
        "none": "disabled",
    }.get(transport, "disabled")
    reason = mailer_reason_code()
    configured = email_configured()
    return {
        "mailer_enabled": configured,
        "provider": provider,
        "configuration_valid": configured and reason == "ok",
        "sender_configured": bool(settings.effective_platform_from),
        "provider_reachable": None,
        "reason_code": reason if not configured else "ok",
    }


def email_status_public() -> dict:
    """État e-mail plateforme (sans secrets) pour diagnostic admin."""
    from_email = settings.effective_platform_from
    key = _brevo_api_key()
    key_prefix = ""
    key_suffix = ""
    if key:
        key_prefix = key[:10]
        key_suffix = key[-4:] if len(key) > 4 else ""
    looks_smtp_key = key.lower().startswith("xsmtpsib-")
    diagnostic = mailer_diagnostic()
    return {
        "configured": email_configured(),
        "transport": email_transport(),
        "smtp_ready": smtp_ready(),
        "has_smtp_host": bool(settings.smtp_host.strip()),
        "has_smtp_user": bool(settings.smtp_user.strip()),
        "has_smtp_password": bool(settings.smtp_password.strip()),
        **_smtp_user_public(),
        "has_brevo_api_key": bool(key),
        "brevo_key_looks_valid": brevo_api_ready(),
        "brevo_key_is_smtp_key_by_mistake": looks_smtp_key,
        "brevo_key_prefix": key_prefix,
        "brevo_key_suffix": key_suffix,
        "brevo_key_length": len(key),
        "has_platform_from": bool(from_email),
        "platform_from": from_email,
        "platform_from_name": settings.effective_platform_from_name,
        **diagnostic,
    }


def probe_brevo_account() -> dict:
    """Diagnostic non destructif API + SMTP (aucun e-mail envoyé)."""
    status = email_status_public()
    live = PlatformEmailProvider(http_get=httpx.get).health(live=True)
    api = live.get("brevo_api") or {}
    smtp = live.get("smtp") or {}
    reason = live.get("reason_code") or status.get("reason_code") or "provider_not_configured"
    api_ok = api.get("auth") == "ok"
    smtp_ok = smtp.get("auth") == "ok"
    reachable = api_ok or smtp_ok
    hint = ""
    if reason == "ok":
        if api_ok and not smtp_ok and smtp.get("configured"):
            hint = "API Brevo authentifiée. Le fallback SMTP n’est pas authentifié."
        elif smtp_ok and not api_ok and api.get("configured"):
            hint = "SMTP plateforme authentifié. L’API Brevo n’est pas authentifiée."
        else:
            hint = "Canal plateforme prêt."
    elif reason == "authentication_failed":
        hint = "Authentification fournisseur refusée. Vérifiez BREVO_API_KEY et/ou SMTP_PASSWORD."
    elif reason == "sender_not_configured":
        hint = "Renseignez PLATFORM_EMAIL_FROM."
    merged = {
        **status,
        "brevo_ok": api_ok or smtp_ok,
        "brevo_http": api.get("http_status"),
        "brevo_error": "" if api_ok else (reason if api.get("configured") else ""),
        "smtp_probe_error": "" if smtp_ok else (smtp.get("connect") if smtp.get("configured") else ""),
        "provider_reachable": reachable,
        "reason_code": reason,
        "hint": hint,
        "preferred_transport": live.get("preferred_transport"),
        "fallback_available": live.get("fallback_available"),
        "brevo_api_health": api,
        "smtp_health": smtp,
        "platform_from_configured": live.get("platform_from_configured"),
    }
    return merged


def send_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    attachments: list[MailAttachment] | None = None,
    sender_name: str | None = None,
    sender_email: str | None = None,
    reply_to_email: str | None = None,
    reply_to_name: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
) -> SendEmailResult:
    """Envoie un e-mail via l'infrastructure plateforme. Ne jamais exposer de secret."""
    provider = PlatformEmailProvider(
        http_post=httpx.post,
        smtp_send=_send_via_smtp,
    )
    result: ProviderSendResult = provider.send(
        to_email=to_email,
        subject=subject,
        body=body,
        attachments=attachments,
        sender_name=sender_name,
        sender_email=sender_email,
        reply_to_email=reply_to_email,
        reply_to_name=reply_to_name,
        cc=cc,
        bcc=bcc,
        html_body=html_body,
    )
    persisted_provider = "brevo" if result.transport == "brevo_api" else "smtp"
    return SendEmailResult(
        provider=persisted_provider,
        provider_message_id=result.provider_message_id,
        sender_email=result.sender_email,
        sender_name=result.sender_name,
        transport=result.transport,
        used_fallback=result.used_fallback,
    )


def _send_via_brevo(
    *,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None,
    attachments: list[MailAttachment],
    from_email: str,
    from_name: str,
    reply_to_email: str | None,
    reply_to_name: str | None,
    cc: list[str],
    bcc: list[str],
) -> SendEmailResult:
    result = send_via_brevo_api(
        to_email=to_email,
        subject=subject,
        body=body,
        html_body=html_body,
        attachments=attachments,
        from_email=from_email,
        from_name=from_name,
        reply_to_email=reply_to_email,
        reply_to_name=reply_to_name,
        cc=cc,
        bcc=bcc,
        http_post=httpx.post,
    )
    return SendEmailResult(
        provider="brevo",
        provider_message_id=result.provider_message_id,
        sender_email=result.sender_email,
        sender_name=result.sender_name,
        transport="brevo_api",
    )


def _send_via_smtp(
    *,
    to_email: str,
    subject: str,
    body: str,
    attachments: list[MailAttachment],
    from_email: str,
    from_name: str,
    reply_to_email: str | None,
    cc: list[str],
    bcc: list[str],
) -> None:
    send_via_platform_smtp(
        to_email=to_email,
        subject=subject,
        body=body,
        attachments=attachments,
        from_email=from_email,
        from_name=from_name,
        reply_to_email=reply_to_email,
        cc=cc,
        bcc=bcc,
    )
