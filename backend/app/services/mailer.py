from __future__ import annotations

import base64
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage

import httpx

from app.config import settings


@dataclass(frozen=True)
class MailAttachment:
    filename: str
    content: bytes
    maintype: str = "application"
    subtype: str = "octet-stream"


@dataclass(frozen=True)
class SendEmailResult:
    provider: str
    provider_message_id: str = ""
    sender_email: str = ""
    sender_name: str = ""


def email_configured() -> bool:
    """True si Brevo API ou SMTP classique est prêt (clés plateforme uniquement)."""
    if settings.brevo_api_key.strip() and settings.effective_platform_from:
        return True
    return bool(settings.smtp_host.strip() and settings.effective_platform_from)


def email_transport() -> str:
    if settings.brevo_api_key.strip() and settings.effective_platform_from:
        return "brevo"
    if settings.smtp_host.strip() and settings.effective_platform_from:
        return "smtp"
    return "none"


def email_status_public() -> dict:
    """État e-mail plateforme (sans secrets) pour diagnostic admin."""
    from_email = settings.effective_platform_from
    return {
        "configured": email_configured(),
        "transport": email_transport(),
        "has_brevo_api_key": bool(settings.brevo_api_key.strip()),
        "has_platform_from": bool(from_email),
        "platform_from": from_email,
        "platform_from_name": settings.effective_platform_from_name,
    }


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
    """Envoie un e-mail via l'infrastructure plateforme. Ne jamais exposer BREVO_API_KEY."""
    recipient = (to_email or "").strip()
    if not recipient:
        raise RuntimeError("Adresse e-mail destinataire manquante")
    if not email_configured():
        raise RuntimeError(
            "Le service d’envoi est temporairement indisponible. "
            "Contactez le support ComptaPilot."
        )

    from_email = (sender_email or settings.effective_platform_from).strip()
    from_name = (sender_name or settings.effective_platform_from_name).strip() or "ComptaPilot"
    transport = email_transport()

    if transport == "brevo":
        return _send_via_brevo(
            to_email=recipient,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachments or [],
            from_email=from_email,
            from_name=from_name,
            reply_to_email=(reply_to_email or "").strip() or None,
            reply_to_name=(reply_to_name or "").strip() or None,
            cc=[e.strip() for e in (cc or []) if e and e.strip()],
            bcc=[e.strip() for e in (bcc or []) if e and e.strip()],
        )

    _send_via_smtp(
        to_email=recipient,
        subject=subject,
        body=body,
        attachments=attachments or [],
        from_email=from_email,
        from_name=from_name,
        reply_to_email=(reply_to_email or "").strip() or None,
        cc=[e.strip() for e in (cc or []) if e and e.strip()],
        bcc=[e.strip() for e in (bcc or []) if e and e.strip()],
    )
    return SendEmailResult(
        provider="smtp",
        sender_email=from_email,
        sender_name=from_name,
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
    payload: dict = {
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

    response = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": settings.brevo_api_key.strip(),
            "accept": "application/json",
            "content-type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )
    if response.status_code >= 400:
        detail = ""
        try:
            data = response.json()
            detail = str(
                data.get("message")
                or data.get("code")
                or (data.get("error") if isinstance(data.get("error"), str) else "")
                or response.text[:280]
            )
        except Exception:  # noqa: BLE001
            detail = (response.text or "")[:280]
        hint = (
            "Sur Render → Environment : collez une vraie clé API Brevo dans BREVO_API_KEY "
            "(SMTP & API → API Keys), puis PLATFORM_EMAIL_FROM=contact@elfis-core.com "
            "(expéditeur validé dans Brevo)."
        )
        if "key not found" in detail.lower() or "unauthorized" in detail.lower():
            raise RuntimeError(
                "Clé Brevo invalide ou absente (Key not found). " + hint
            )
        raise RuntimeError(
            "Brevo a refusé l’envoi"
            + (f" ({detail})" if detail else f" (HTTP {response.status_code})")
            + ". "
            + hint
        )

    message_id = ""
    try:
        data = response.json()
        message_id = str(data.get("messageId") or data.get("message_id") or "")
    except Exception:  # noqa: BLE001
        message_id = ""

    return SendEmailResult(
        provider="brevo",
        provider_message_id=message_id,
        sender_email=from_email,
        sender_name=from_name,
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
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg, to_addrs=recipients)
