from __future__ import annotations

from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode
import base64

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import OrganizationEmailConnection
from app.services.email_connections import (
    create_oauth_state,
    get_access_token,
    get_refresh_token,
    mark_connection_error,
    store_oauth_tokens,
    upsert_provider_connection,
)
from app.services.mailer import MailAttachment, SendEmailResult

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GOOGLE_REVOKE = "https://oauth2.googleapis.com/revoke"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.send",
]


def google_oauth_configured() -> bool:
    return bool(
        settings.google_client_id.strip()
        and settings.google_client_secret.strip()
        and settings.google_oauth_redirect_uri.strip()
    )


def build_google_authorize_url(
    *,
    organization_id: int,
    user_id: int,
    connection_id: int | None = None,
) -> str:
    if not google_oauth_configured():
        raise RuntimeError("Google OAuth non configuré (GOOGLE_CLIENT_ID / SECRET / REDIRECT_URI)")
    state = create_oauth_state(
        organization_id=organization_id,
        user_id=user_id,
        provider="google",
        connection_id=connection_id,
    )
    params = {
        "client_id": settings.google_client_id.strip(),
        "redirect_uri": settings.google_oauth_redirect_uri.strip(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH}?{urlencode(params)}"


def exchange_google_code(code: str) -> dict:
    response = httpx.post(
        GOOGLE_TOKEN,
        data={
            "code": code,
            "client_id": settings.google_client_id.strip(),
            "client_secret": settings.google_client_secret.strip(),
            "redirect_uri": settings.google_oauth_redirect_uri.strip(),
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    if response.status_code >= 400:
        raise RuntimeError("Échange du code Google impossible")
    return response.json()


def fetch_google_profile(access_token: str) -> dict:
    response = httpx.get(
        GOOGLE_USERINFO,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20.0,
    )
    if response.status_code >= 400:
        raise RuntimeError("Profil Google inaccessible")
    return response.json()


def complete_google_oauth(
    db: Session,
    *,
    organization_id: int,
    user_id: int,
    code: str,
    connection_id: int | None = None,
) -> OrganizationEmailConnection:
    tokens = exchange_google_code(code)
    access = tokens.get("access_token") or ""
    refresh = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")
    if not access:
        raise RuntimeError("Jeton Google manquant")
    profile = fetch_google_profile(access)
    email = (profile.get("email") or "").strip()
    if not email:
        raise RuntimeError("Adresse Google introuvable")
    return upsert_provider_connection(
        db,
        organization_id=organization_id,
        provider="google",
        user_id=user_id,
        email=email,
        display_name=(profile.get("name") or email).strip(),
        access_token=access,
        refresh_token=refresh,
        expires_in=int(expires_in) if expires_in else 3600,
        provider_account_id=str(profile.get("id") or ""),
        connection_id=connection_id,
        make_default=True,
    )


def refresh_google_access_token(
    db: Session, conn: OrganizationEmailConnection
) -> str:
    refresh = get_refresh_token(conn)
    if not refresh:
        mark_connection_error(
            db, conn, code="token_expired", message="Reconnectez votre boîte Google.", status="expired"
        )
        raise RuntimeError(
            "Votre connexion Google a expiré. Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
        )
    response = httpx.post(
        GOOGLE_TOKEN,
        data={
            "client_id": settings.google_client_id.strip(),
            "client_secret": settings.google_client_secret.strip(),
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
        timeout=30.0,
    )
    if response.status_code >= 400:
        mark_connection_error(
            db,
            conn,
            code="revoked",
            message="Consentement Google retiré ou jeton révoqué. Reconnectez la boîte.",
            status="revoked",
        )
        raise RuntimeError(
            "Votre connexion Google a expiré. Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
        )
    data = response.json()
    access = data.get("access_token") or ""
    if not access:
        raise RuntimeError("Refresh Google échoué")
    store_oauth_tokens(
        conn,
        access_token=access,
        refresh_token=refresh,
        expires_in=int(data.get("expires_in") or 3600),
        email=conn.email_address,
        display_name=conn.display_name,
        provider_account_id=conn.provider_account_id,
    )
    conn.status = "connected"
    db.add(conn)
    db.commit()
    return access


def ensure_google_access_token(db: Session, conn: OrganizationEmailConnection) -> str:
    if conn.token_expires_at and conn.token_expires_at > datetime.utcnow():
        try:
            return get_access_token(conn)
        except Exception:  # noqa: BLE001
            pass
    return refresh_google_access_token(db, conn)


def revoke_google_token(conn: OrganizationEmailConnection) -> None:
    try:
        token = get_refresh_token(conn) or get_access_token(conn)
        if token:
            httpx.post(GOOGLE_REVOKE, params={"token": token}, timeout=15.0)
    except Exception:  # noqa: BLE001
        return


def send_via_gmail(
    db: Session,
    conn: OrganizationEmailConnection,
    *,
    to_email: str,
    subject: str,
    body: str,
    attachments: list[MailAttachment] | None = None,
    reply_to_email: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> SendEmailResult:
    access = ensure_google_access_token(db, conn)
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["From"] = f"{conn.display_name} <{conn.email_address}>" if conn.display_name else conn.email_address
    msg["Subject"] = subject
    if reply_to_email:
        msg["Reply-To"] = reply_to_email
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg.attach(MIMEText(body, "plain", "utf-8"))
    for item in attachments or []:
        part = MIMEApplication(item.content, Name=item.filename)
        part["Content-Disposition"] = f'attachment; filename="{item.filename}"'
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    response = httpx.post(
        GOOGLE_GMAIL_SEND,
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json",
        },
        json={"raw": raw},
        timeout=60.0,
    )
    if response.status_code >= 400:
        lower = response.text.lower()
        if response.status_code in (401, 403) or "invalid_grant" in lower:
            mark_connection_error(
                db,
                conn,
                code="revoked",
                message="Connexion Google révoquée. Reconnectez la boîte.",
                status="revoked",
            )
            raise RuntimeError(
                "Votre connexion Google a expiré. Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
            )
        mark_connection_error(
            db, conn, code="provider_error", message="Échec d’envoi Gmail.", status="error"
        )
        raise RuntimeError("L’e-mail n’a pas pu être envoyé via Gmail.")

    message_id = ""
    try:
        message_id = str(response.json().get("id") or "")
    except Exception:  # noqa: BLE001
        message_id = ""

    return SendEmailResult(
        provider="google",
        provider_message_id=message_id,
        sender_email=conn.email_address,
        sender_name=conn.display_name or "",
    )
