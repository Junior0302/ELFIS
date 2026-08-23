from __future__ import annotations

import base64
import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Callable

import httpx

from app.config import settings
from app.services.email_providers.types import (
    DEFAULT_SENDER_NAME,
    EmailProviderError,
    FALLBACK_COMPATIBLE_ERRORS,
    ProviderSendResult,
    pick_preferred_error,
    user_safe_message,
)
from app.services.mailer_types import MailAttachment

logger = logging.getLogger(__name__)

BREVO_SMTP_EMAIL_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_ACCOUNT_URL = "https://api.brevo.com/v3/account"

HttpPost = Callable[..., Any]
HttpGet = Callable[..., Any]
SmtpSend = Callable[..., None]


def _normalize_credential(value: str) -> str:
    cleaned = settings._clean_secret(value)
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0"):
        cleaned = cleaned.replace(ch, "")
    return cleaned.strip()


def _brevo_api_key() -> str:
    return settings._clean_secret(settings.brevo_api_key)


def platform_from_configured() -> bool:
    return bool(settings.effective_platform_from)


def smtp_ready() -> bool:
    return bool(
        settings.smtp_host.strip()
        and settings.effective_platform_from
        and settings.smtp_user.strip()
        and settings.smtp_password.strip()
    )


def brevo_api_key_format_usable(key: str | None = None) -> bool:
    raw = _brevo_api_key() if key is None else key
    if not raw:
        return False
    if raw.lower().startswith("xsmtpsib-"):
        return False
    return raw.startswith("xkeysib-") and len(raw) > 40


def brevo_api_ready() -> bool:
    return bool(platform_from_configured() and brevo_api_key_format_usable())


def preferred_transport() -> str:
    if brevo_api_ready():
        return "brevo_api"
    if smtp_ready():
        return "smtp"
    return "none"


def log_email_delivery(
    *,
    transport: str,
    result: str,
    error: str = "",
    status: int | str | None = None,
    smtp_code: str = "",
    fallback: bool = False,
    message_id_present: bool = False,
) -> None:
    """Log interne déterministe — jamais de secret."""
    status = "-" if status is None else str(status)
    logger.info(
        "email_delivery provider=platform transport=%s result=%s status=%s smtp_code=%s "
        "error=%s fallback=%s message_id=%s",
        transport,
        result,
        status,
        smtp_code or "-",
        error or "-",
        "yes" if fallback else "no",
        "yes" if message_id_present else "no",
    )


def classify_brevo_http(status_code: int, detail: str) -> str:
    lower = (detail or "").lower()
    if status_code in (401, 403) or "key not found" in lower or "unauthorized" in lower:
        return "authentication_failed"
    if status_code == 429:
        return "rate_limit"
    if status_code == 408:
        return "timeout"
    if "sender" in lower and (
        "not verified" in lower
        or "unrecognised" in lower
        or "unrecognized" in lower
        or "invalid" in lower
    ):
        return "sender_not_verified"
    if status_code == 400 and (
        "recipient" in lower or "invalid email" in lower or "invalid_parameter" in lower
    ):
        return "recipient_invalid"
    if status_code >= 500:
        return "provider_unreachable"
    return "delivery_failed"


def classify_smtp_exception(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        code = str(getattr(exc, "smtp_code", "") or "535")
        return "authentication_failed", code
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "recipient_invalid", ""
    if isinstance(exc, TimeoutError):
        return "timeout", ""
    text = str(exc).lower()
    if "535" in text or "auth" in text:
        return "authentication_failed", "535" if "535" in text else ""
    if "timed out" in text or "timeout" in text:
        return "timeout", ""
    if isinstance(exc, (smtplib.SMTPConnectError, ConnectionError, OSError)):
        return "provider_unreachable", ""
    return "delivery_failed", ""


def _safe_brevo_detail(response: Any) -> str:
    try:
        data = response.json()
        raw = str(
            data.get("message")
            or data.get("code")
            or (data.get("error") if isinstance(data.get("error"), str) else "")
            or ""
        )
    except Exception:  # noqa: BLE001
        raw = ""
    lower = raw.lower()
    if "key not found" in lower:
        return "key_not_found"
    if "unauthorized" in lower:
        return "unauthorized"
    if "sender" in lower:
        return "sender_rejected"
    if "recipient" in lower or "invalid email" in lower:
        return "invalid email recipient"
    if raw:
        return "provider_rejected"
    return f"http_{getattr(response, 'status_code', 'unknown')}"


def send_via_brevo_api(
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
    http_post: HttpPost | None = None,
) -> ProviderSendResult:
    payload: dict[str, Any] = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }
    if html_body:
        payload["htmlContent"] = html_body
    if reply_to_email:
        payload["replyTo"] = {
            "email": reply_to_email,
            **({"name": reply_to_name} if reply_to_name else {}),
        }
    if cc:
        payload["cc"] = [{"email": e} for e in cc]
    if bcc:
        payload["bcc"] = [{"email": e} for e in bcc]
    if attachments:
        payload["attachment"] = [
            {
                "name": item.filename,
                "content": base64.b64encode(item.content).decode("ascii"),
            }
            for item in attachments
        ]

    api_key = _brevo_api_key()
    if api_key.lower().startswith("xsmtpsib-"):
        raise EmailProviderError("missing_api_key", transport="brevo_api")
    if not api_key.startswith("xkeysib-"):
        raise EmailProviderError("missing_api_key", transport="brevo_api")

    post = http_post or httpx.post
    try:
        response = post(
            BREVO_SMTP_EMAIL_URL,
            headers={
                "api-key": api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
    except httpx.TimeoutException as exc:
        log_email_delivery(transport="brevo_api", result="failed", error="timeout")
        raise EmailProviderError("timeout", transport="brevo_api") from exc
    except Exception as exc:  # noqa: BLE001
        log_email_delivery(transport="brevo_api", result="failed", error="provider_unreachable")
        raise EmailProviderError("provider_unreachable", transport="brevo_api") from exc

    if response.status_code >= 400:
        safe = _safe_brevo_detail(response)
        code = classify_brevo_http(response.status_code, safe)
        log_email_delivery(
            transport="brevo_api",
            result="failed",
            status=response.status_code,
            error=code,
        )
        raise EmailProviderError(
            code,
            transport="brevo_api",
            http_status=response.status_code,
            safe_detail=user_safe_message(code),
        )

    message_id = ""
    try:
        data = response.json()
        message_id = str(data.get("messageId") or data.get("message_id") or "")
    except Exception:  # noqa: BLE001
        message_id = ""

    log_email_delivery(
        transport="brevo_api",
        result="sent",
        status=response.status_code,
        message_id_present=bool(message_id),
    )
    return ProviderSendResult(
        success=True,
        provider="platform",
        transport="brevo_api",
        provider_message_id=message_id,
        sender_email=from_email,
        sender_name=from_name,
        http_status=response.status_code,
    )


def send_via_platform_smtp(
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
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to_email
    if reply_to_email:
        msg["Reply-To"] = reply_to_email
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(body)
    for item in attachments:
        msg.add_attachment(
            item.content,
            maintype=item.maintype,
            subtype=item.subtype,
            filename=item.filename,
        )
    recipients = [to_email, *cc, *bcc]
    user = _normalize_credential(settings.smtp_user)
    password = _normalize_credential(settings.smtp_password)
    host = settings.smtp_host.strip()
    try:
        with smtplib.SMTP(host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg, to_addrs=recipients)
    except Exception as exc:
        code, smtp_code = classify_smtp_exception(exc)
        log_email_delivery(
            transport="smtp",
            result="failed",
            smtp_code=smtp_code,
            error=code,
        )
        raise EmailProviderError(code, transport="smtp", smtp_code=smtp_code) from exc


def probe_smtp_login() -> dict[str, str]:
    """Login + NOOP — n’envoie aucun e-mail. Aucun secret dans le résultat."""
    host = settings.smtp_host.strip()
    user = _normalize_credential(settings.smtp_user)
    password = _normalize_credential(settings.smtp_password)
    if not host or not user or not password:
        return {"connect": "skipped", "auth": "skipped", "error": "not_configured"}
    try:
        with smtplib.SMTP(host, settings.smtp_port, timeout=25) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(user, password)
            smtp.noop()
        return {"connect": "ok", "auth": "ok", "error": ""}
    except smtplib.SMTPAuthenticationError:
        return {"connect": "ok", "auth": "failed", "error": "authentication_failed"}
    except (smtplib.SMTPConnectError, ConnectionError, OSError, TimeoutError):
        return {"connect": "failed", "auth": "skipped", "error": "provider_unreachable"}
    except Exception:  # noqa: BLE001
        return {"connect": "failed", "auth": "skipped", "error": "provider_unreachable"}


def probe_brevo_api_account(http_get: HttpGet | None = None) -> dict[str, Any]:
    """GET /v3/account — n’envoie aucun e-mail. Aucun secret dans le résultat."""
    key = _brevo_api_key()
    if not key:
        return {
            "configured": False,
            "format_usable": False,
            "auth": "skipped",
            "http_status": None,
            "error": "not_configured",
        }
    format_ok = brevo_api_key_format_usable(key)
    if not format_ok:
        return {
            "configured": True,
            "format_usable": False,
            "auth": "skipped",
            "http_status": None,
            "error": "missing_api_key",
        }
    get = http_get or httpx.get
    try:
        response = get(
            BREVO_ACCOUNT_URL,
            headers={"api-key": key, "accept": "application/json"},
            timeout=20.0,
        )
    except httpx.TimeoutException:
        return {
            "configured": True,
            "format_usable": True,
            "auth": "unknown",
            "http_status": None,
            "error": "timeout",
        }
    except Exception:  # noqa: BLE001
        return {
            "configured": True,
            "format_usable": True,
            "auth": "unknown",
            "http_status": None,
            "error": "provider_unreachable",
        }
    if response.status_code in (401, 403):
        return {
            "configured": True,
            "format_usable": True,
            "auth": "failed",
            "http_status": response.status_code,
            "error": "authentication_failed",
        }
    if response.status_code >= 400:
        return {
            "configured": True,
            "format_usable": True,
            "auth": "unknown",
            "http_status": response.status_code,
            "error": "provider_unreachable",
        }
    return {
        "configured": True,
        "format_usable": True,
        "auth": "ok",
        "http_status": response.status_code,
        "error": "",
    }


class PlatformEmailProvider:
    """Transport plateforme : Brevo API prioritaire, SMTP en fallback."""

    name = "platform"

    def __init__(
        self,
        *,
        http_post: HttpPost | None = None,
        http_get: HttpGet | None = None,
        smtp_send: SmtpSend | None = None,
    ) -> None:
        self._http_post = http_post
        self._http_get = http_get
        self._smtp_send = smtp_send

    def health(self, *, live: bool = False) -> dict[str, Any]:
        key = _brevo_api_key()
        api_configured = bool(key)
        api_format = brevo_api_key_format_usable(key) if key else False
        smtp_configured = bool(
            settings.smtp_host.strip()
            and settings.smtp_user.strip()
            and settings.smtp_password.strip()
        )
        from_ok = platform_from_configured()
        preferred = preferred_transport()
        snapshot: dict[str, Any] = {
            "provider": "platform",
            "preferred_transport": preferred,
            "fallback_available": smtp_ready() and preferred == "brevo_api",
            "platform_from_configured": from_ok,
            "brevo_api": {
                "configured": api_configured,
                "format_usable": api_format,
                "auth": "skipped",
                "http_status": None,
            },
            "smtp": {
                "configured": smtp_configured,
                "connect": "skipped" if not smtp_configured else ("skipped" if not live else "unknown"),
                "auth": "skipped" if not smtp_configured else ("skipped" if not live else "unknown"),
            },
            "reason_code": _config_reason_code(),
        }
        if not live:
            return snapshot

        if api_configured:
            api = probe_brevo_api_account(self._http_get)
            snapshot["brevo_api"] = {
                "configured": True,
                "format_usable": bool(api.get("format_usable")),
                "auth": api.get("auth") or "skipped",
                "http_status": api.get("http_status"),
            }
            if api.get("error") and api["error"] != "not_configured":
                snapshot["reason_code"] = api["error"]
        if smtp_configured:
            smtp = probe_smtp_login()
            snapshot["smtp"] = {
                "configured": True,
                "connect": smtp.get("connect") or "skipped",
                "auth": smtp.get("auth") or "skipped",
            }
            if smtp.get("error") == "authentication_failed" and snapshot["brevo_api"].get("auth") != "ok":
                snapshot["reason_code"] = "authentication_failed"
            elif smtp.get("error") == "provider_unreachable" and snapshot["brevo_api"].get("auth") not in {
                "ok",
                "failed",
            }:
                snapshot["reason_code"] = "provider_unreachable"

        api_auth = snapshot["brevo_api"].get("auth")
        smtp_auth = snapshot["smtp"].get("auth")
        if preferred == "brevo_api" and api_auth == "ok":
            snapshot["reason_code"] = "ok"
        elif preferred == "smtp" and smtp_auth == "ok":
            snapshot["reason_code"] = "ok"
        elif api_auth == "ok" or smtp_auth == "ok":
            snapshot["reason_code"] = "ok"
        elif api_auth == "failed" or smtp_auth == "failed":
            snapshot["reason_code"] = "authentication_failed"
        return snapshot

    def send(
        self,
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
    ) -> ProviderSendResult:
        recipient = (to_email or "").strip()
        if not recipient:
            raise EmailProviderError("recipient_missing", transport="none")
        if not brevo_api_ready() and not smtp_ready():
            raise EmailProviderError(_config_reason_code(), transport="none")

        from_email = (sender_email or settings.effective_platform_from).strip()
        from_name = (sender_name or settings.effective_platform_from_name).strip() or DEFAULT_SENDER_NAME
        cc_list = [e.strip() for e in (cc or []) if e and e.strip()]
        bcc_list = [e.strip() for e in (bcc or []) if e and e.strip()]
        reply_email = (reply_to_email or "").strip() or None
        reply_name = (reply_to_name or "").strip() or None
        files = attachments or []

        api_error: EmailProviderError | None = None
        if brevo_api_ready():
            try:
                return send_via_brevo_api(
                    to_email=recipient,
                    subject=subject,
                    body=body,
                    html_body=html_body,
                    attachments=files,
                    from_email=from_email,
                    from_name=from_name,
                    reply_to_email=reply_email,
                    reply_to_name=reply_name,
                    cc=cc_list,
                    bcc=bcc_list,
                    http_post=self._http_post,
                )
            except EmailProviderError as exc:
                api_error = exc
                if exc.error_code not in FALLBACK_COMPATIBLE_ERRORS or not smtp_ready():
                    raise

        if smtp_ready():
            try:
                smtp_fn = self._smtp_send or send_via_platform_smtp
                smtp_fn(
                    to_email=recipient,
                    subject=subject,
                    body=body,
                    attachments=files,
                    from_email=from_email,
                    from_name=from_name,
                    reply_to_email=reply_email,
                    cc=cc_list,
                    bcc=bcc_list,
                )
                log_email_delivery(
                    transport="smtp",
                    result="sent",
                    fallback=api_error is not None,
                )
                return ProviderSendResult(
                    success=True,
                    provider="platform",
                    transport="smtp",
                    sender_email=from_email,
                    sender_name=from_name,
                    used_fallback=api_error is not None,
                )
            except EmailProviderError as smtp_error:
                chosen = (
                    pick_preferred_error(api_error.error_code, smtp_error.error_code)
                    if api_error
                    else smtp_error.error_code
                )
                winner = api_error if api_error and chosen == api_error.error_code else smtp_error
                log_email_delivery(
                    transport=winner.transport or "smtp",
                    result="failed",
                    status=winner.http_status,
                    smtp_code=winner.smtp_code,
                    error=chosen,
                    fallback=api_error is not None,
                )
                raise EmailProviderError(
                    chosen,
                    transport=winner.transport,
                    http_status=winner.http_status,
                    smtp_code=winner.smtp_code,
                    used_fallback=api_error is not None,
                ) from smtp_error
            except Exception as exc:
                code, smtp_code = classify_smtp_exception(exc)
                chosen = pick_preferred_error(api_error.error_code, code) if api_error else code
                raise EmailProviderError(
                    chosen,
                    transport="smtp",
                    smtp_code=smtp_code,
                    used_fallback=api_error is not None,
                ) from exc

        if api_error:
            raise api_error
        raise EmailProviderError("provider_not_configured", transport="none")


def _config_reason_code() -> str:
    from_email = settings.effective_platform_from
    if not from_email:
        return "sender_not_configured"
    smtp_host = settings.smtp_host.strip()
    smtp_user = settings.smtp_user.strip()
    smtp_password = settings.smtp_password.strip()
    key = _brevo_api_key()
    if smtp_host or smtp_user or smtp_password:
        missing_smtp = not (smtp_host and smtp_user and smtp_password)
        if missing_smtp and not brevo_api_ready():
            return "missing_smtp_credentials"
    if key:
        if key.lower().startswith("xsmtpsib-"):
            return "missing_api_key"
        if not (key.startswith("xkeysib-") and len(key) > 40):
            return "missing_api_key"
    if brevo_api_ready() or smtp_ready():
        return "ok"
    if not key and not (smtp_host and smtp_user and smtp_password):
        return "provider_not_configured"
    return "provider_not_configured"
