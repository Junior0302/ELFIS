from __future__ import annotations

import base64
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage

import httpx

from app.config import settings


def _normalize_credential(value: str) -> str:
    """Nettoie les secrets collés depuis Render (guillemets, espaces invisibles)."""
    cleaned = settings._clean_secret(value)
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0"):
        cleaned = cleaned.replace(ch, "")
    return cleaned.strip()


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


def _smtp_ready() -> bool:
    return bool(
        settings.smtp_host.strip()
        and settings.effective_platform_from
        and settings.smtp_user.strip()
        and settings.smtp_password.strip()
    )


def _smtp_user_public() -> dict:
    """Infos non secrètes sur SMTP_USER pour diagnostiquer un 535."""
    user = _normalize_credential(settings.smtp_user)
    password = _normalize_credential(settings.smtp_password)
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
    """Vrai test d’auth SMTP (login + NOOP)."""
    host = settings.smtp_host.strip()
    user = _normalize_credential(settings.smtp_user)
    password = _normalize_credential(settings.smtp_password)
    if not host or not user or not password:
        return False, "SMTP incomplet : SMTP_HOST, SMTP_USER et SMTP_PASSWORD requis."
    try:
        with smtplib.SMTP(host, settings.smtp_port, timeout=25) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(user, password)
            smtp.noop()
        return True, ""
    except smtplib.SMTPAuthenticationError as exc:
        public = _smtp_user_public()
        if user.lower().endswith("@smtp-brevo.com") and public["smtp_password_looks_brevo"]:
            hint = (
                "Auth SMTP refusée (535) alors que login @smtp-brevo.com et forme xsmtpsib- sont OK. "
                "La clé sur Render est probablement obsolète/incomplète, ou le filtrage IP SMTP "
                "est activé dans Brevo. Régénérez une clé SMTP, collez-la dans SMTP_PASSWORD, "
                "désactivez Authorized IPs, Manual Deploy."
            )
        else:
            hint = (
                "Auth SMTP refusée (535). "
                "SMTP_USER doit être le login Brevo (…@smtp-brevo.com), "
                "pas contact@ ni votre e-mail perso. "
                "SMTP_PASSWORD = clé xsmtpsib-… (pas xkeysib-…)."
            )
            if not user.lower().endswith("@smtp-brevo.com"):
                hint += (
                    f" Login actuel (masqué) : {public['smtp_user_masked']} — forme incorrecte."
                )
        return False, f"{hint} Détail: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Connexion SMTP impossible: {exc}"


def _brevo_api_key() -> str:
    return settings._clean_secret(settings.brevo_api_key)


def _brevo_api_key_usable() -> bool:
    """Clé API Brevo (xkeysib-…), pas la clé SMTP (xsmtpsib-…)."""
    key = _brevo_api_key()
    if not key or not settings.effective_platform_from:
        return False
    if key.lower().startswith("xsmtpsib-"):
        return False
    return key.startswith("xkeysib-") and len(key) > 40


def email_configured() -> bool:
    """True si SMTP Brevo ou API Brevo est prêt (clés plateforme uniquement)."""
    if _smtp_ready():
        return True
    return _brevo_api_key_usable()


def email_transport() -> str:
    # SMTP prioritaire si configuré (souvent OK même quand la clé API est refusée).
    # API Brevo en secours / si SMTP absent.
    if _smtp_ready():
        return "smtp"
    if _brevo_api_key_usable():
        return "brevo"
    return "none"


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
    return {
        "configured": email_configured(),
        "transport": email_transport(),
        "smtp_ready": _smtp_ready(),
        "has_smtp_host": bool(settings.smtp_host.strip()),
        "has_smtp_user": bool(settings.smtp_user.strip()),
        "has_smtp_password": bool(settings.smtp_password.strip()),
        **_smtp_user_public(),
        "has_brevo_api_key": bool(key),
        "brevo_key_looks_valid": _brevo_api_key_usable(),
        "brevo_key_is_smtp_key_by_mistake": looks_smtp_key,
        "brevo_key_prefix": key_prefix,
        "brevo_key_suffix": key_suffix,
        "brevo_key_length": len(key),
        "has_platform_from": bool(from_email),
        "platform_from": from_email,
        "platform_from_name": settings.effective_platform_from_name,
    }


def probe_brevo_account() -> dict:
    """Valide SMTP par login réel (prioritaire) ou ping API Brevo."""
    status = email_status_public()
    if status["smtp_ready"]:
        ok, error = _probe_smtp_login()
        if ok:
            return {
                **status,
                "brevo_ok": True,
                "brevo_error": "",
                "hint": (
                    "Auth SMTP Brevo validée "
                    f"({settings.smtp_host.strip()} → {status['platform_from']})."
                ),
            }
        # SMTP HS : continuer vers le test API pour un diagnostic complet
        status = {
            **status,
            "smtp_probe_error": error,
        }
    key = _brevo_api_key()
    if not key:
        return {
            **status,
            "brevo_ok": False,
            "brevo_error": (
                "Ni SMTP ni clé API. Sur Render ajoutez SMTP_HOST / SMTP_USER / "
                "SMTP_PASSWORD (clé SMTP Brevo) ou BREVO_API_KEY."
            ),
        }
    if key.lower().startswith("xsmtpsib-"):
        return {
            **status,
            "brevo_ok": False,
            "brevo_error": "BREVO_API_KEY contient une clé SMTP (xsmtpsib-).",
            "hint": (
                "Dans Brevo → SMTP & API → Clés API, créez une clé API (xkeysib-…) "
                "et mettez-la dans BREVO_API_KEY. La clé xsmtpsib- va dans SMTP_PASSWORD."
            ),
        }
    try:
        response = httpx.get(
            "https://api.brevo.com/v3/account",
            headers={
                "api-key": key,
                "accept": "application/json",
            },
            timeout=20.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {**status, "brevo_ok": False, "brevo_error": f"Réseau Brevo: {exc}"}

    if response.status_code >= 400:
        detail = ""
        try:
            data = response.json()
            detail = str(data.get("message") or data.get("code") or response.text[:200])
        except Exception:  # noqa: BLE001
            detail = (response.text or "")[:200]
        return {
            **status,
            "brevo_ok": False,
            "brevo_http": response.status_code,
            "brevo_error": detail or f"HTTP {response.status_code}",
            "hint": (
                "Regénérez une clé API dans Brevo (SMTP & API → API Keys), "
                "collez-la dans Render BREVO_API_KEY sans guillemets, puis Manual Deploy."
            ),
        }

    email = ""
    try:
        data = response.json()
        email = str(data.get("email") or "")
    except Exception:  # noqa: BLE001
        email = ""
    return {
        **status,
        "brevo_ok": True,
        "brevo_http": response.status_code,
        "brevo_account_email": email,
        "hint": "Clé Brevo acceptée. Si l’envoi échoue encore, validez contact@ comme expéditeur.",
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
    cc_list = [e.strip() for e in (cc or []) if e and e.strip()]
    bcc_list = [e.strip() for e in (bcc or []) if e and e.strip()]
    reply_email = (reply_to_email or "").strip() or None
    reply_name = (reply_to_name or "").strip() or None
    files = attachments or []

    def _via_brevo() -> SendEmailResult:
        return _send_via_brevo(
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
        )

    def _via_smtp() -> SendEmailResult:
        _send_via_smtp(
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
        return SendEmailResult(
            provider="smtp",
            sender_email=from_email,
            sender_name=from_name,
        )

    # SMTP d’abord (souvent OK même si la clé API est refusée), puis API en secours.
    errors: list[str] = []
    if _smtp_ready():
        try:
            return _via_smtp()
        except RuntimeError as smtp_exc:
            errors.append(str(smtp_exc))
    if _brevo_api_key_usable():
        try:
            return _via_brevo()
        except RuntimeError as api_exc:
            errors.append(str(api_exc))
    if errors:
        raise RuntimeError(" | ".join(errors[:2]))
    raise RuntimeError(
        "Aucun canal d’envoi disponible. Configurez SMTP_* ou BREVO_API_KEY sur Render."
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

    api_key = _brevo_api_key()
    if api_key.lower().startswith("xsmtpsib-"):
        raise RuntimeError(
            "BREVO_API_KEY contient une clé SMTP (xsmtpsib-). "
            "Utilisez une clé API (xkeysib-…) dans BREVO_API_KEY, "
            "et xsmtpsib-… uniquement dans SMTP_PASSWORD."
        )
    if not api_key.startswith("xkeysib-"):
        raise RuntimeError(
            "BREVO_API_KEY invalide : elle doit commencer par xkeysib-. "
            "Sur Render : Manual Deploy après avoir collé la clé (sans guillemets)."
        )

    response = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": api_key,
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
            "Sur Render → Environment → BREVO_API_KEY : collez une clé API xkeysib-… "
            "sans guillemets, puis Manual Deploy (pas seulement Save)."
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
    except smtplib.SMTPAuthenticationError as exc:
        masked = _smtp_user_public()["smtp_user_masked"] or "—"
        raise RuntimeError(
            "Auth SMTP Brevo refusée (535). "
            f"Login utilisé (masqué) : {masked}. "
            "SMTP_USER doit être …@smtp-brevo.com ; "
            "SMTP_PASSWORD = clé xsmtpsib-… . "
            f"Détail: {exc}"
        ) from exc
