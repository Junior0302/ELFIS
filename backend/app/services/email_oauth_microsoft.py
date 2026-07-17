from __future__ import annotations

from datetime import datetime
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

SCOPES = [
    "openid",
    "email",
    "profile",
    "offline_access",
    "Mail.Send",
]


def _tenant() -> str:
    return (settings.microsoft_tenant_id or "common").strip() or "common"


def microsoft_oauth_configured() -> bool:
    return bool(
        settings.microsoft_client_id.strip()
        and settings.microsoft_client_secret.strip()
        and settings.microsoft_oauth_redirect_uri.strip()
    )


def build_microsoft_authorize_url(
    *,
    organization_id: int,
    user_id: int,
    connection_id: int | None = None,
) -> str:
    if not microsoft_oauth_configured():
        raise RuntimeError(
            "Microsoft OAuth non configuré (MICROSOFT_CLIENT_ID / SECRET / REDIRECT_URI)"
        )
    state = create_oauth_state(
        organization_id=organization_id,
        user_id=user_id,
        provider="microsoft",
        connection_id=connection_id,
    )
    params = {
        "client_id": settings.microsoft_client_id.strip(),
        "response_type": "code",
        "redirect_uri": settings.microsoft_oauth_redirect_uri.strip(),
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
        "prompt": "select_account",
    }
    return f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/authorize?{urlencode(params)}"


def exchange_microsoft_code(code: str) -> dict:
    response = httpx.post(
        f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/token",
        data={
            "client_id": settings.microsoft_client_id.strip(),
            "client_secret": settings.microsoft_client_secret.strip(),
            "code": code,
            "redirect_uri": settings.microsoft_oauth_redirect_uri.strip(),
            "grant_type": "authorization_code",
            "scope": " ".join(SCOPES),
        },
        timeout=30.0,
    )
    if response.status_code >= 400:
        text = response.text.lower()
        if "aadsts65001" in text or "consent" in text:
            raise RuntimeError(
                "Consentement administrateur Microsoft requis. Contactez votre admin IT."
            )
        raise RuntimeError("Échange du code Microsoft impossible")
    return response.json()


def fetch_microsoft_profile(access_token: str) -> dict:
    response = httpx.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20.0,
    )
    if response.status_code >= 400:
        raise RuntimeError("Profil Microsoft inaccessible")
    return response.json()


def complete_microsoft_oauth(
    db: Session,
    *,
    organization_id: int,
    user_id: int,
    code: str,
    connection_id: int | None = None,
) -> OrganizationEmailConnection:
    tokens = exchange_microsoft_code(code)
    access = tokens.get("access_token") or ""
    refresh = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")
    if not access:
        raise RuntimeError("Jeton Microsoft manquant")
    profile = fetch_microsoft_profile(access)
    email = (
        profile.get("mail")
        or profile.get("userPrincipalName")
        or ""
    ).strip()
    if not email:
        raise RuntimeError("Adresse Microsoft introuvable")
    name = (profile.get("displayName") or email).strip()
    return upsert_provider_connection(
        db,
        organization_id=organization_id,
        provider="microsoft",
        user_id=user_id,
        email=email,
        display_name=name,
        access_token=access,
        refresh_token=refresh,
        expires_in=int(expires_in) if expires_in else 3600,
        provider_account_id=str(profile.get("id") or ""),
        connection_id=connection_id,
        make_default=True,
    )


def refresh_microsoft_access_token(
    db: Session, conn: OrganizationEmailConnection
) -> str:
    refresh = get_refresh_token(conn)
    if not refresh:
        mark_connection_error(
            db,
            conn,
            code="token_expired",
            message="Reconnectez votre boîte Microsoft.",
            status="expired",
        )
        raise RuntimeError(
            "Votre connexion Microsoft a expiré. Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
        )
    response = httpx.post(
        f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/token",
        data={
            "client_id": settings.microsoft_client_id.strip(),
            "client_secret": settings.microsoft_client_secret.strip(),
            "refresh_token": refresh,
            "grant_type": "refresh_token",
            "scope": " ".join(SCOPES),
        },
        timeout=30.0,
    )
    if response.status_code >= 400:
        mark_connection_error(
            db,
            conn,
            code="revoked",
            message="Consentement Microsoft retiré. Reconnectez la boîte.",
            status="revoked",
        )
        raise RuntimeError(
            "Votre connexion Microsoft a expiré. Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
        )
    data = response.json()
    access = data.get("access_token") or ""
    new_refresh = data.get("refresh_token") or refresh
    if not access:
        raise RuntimeError("Refresh Microsoft échoué")
    store_oauth_tokens(
        conn,
        access_token=access,
        refresh_token=new_refresh,
        expires_in=int(data.get("expires_in") or 3600),
        email=conn.email_address,
        display_name=conn.display_name,
        provider_account_id=conn.provider_account_id,
    )
    conn.status = "connected"
    db.add(conn)
    db.commit()
    return access


def ensure_microsoft_access_token(db: Session, conn: OrganizationEmailConnection) -> str:
    if conn.token_expires_at and conn.token_expires_at > datetime.utcnow():
        try:
            return get_access_token(conn)
        except Exception:  # noqa: BLE001
            pass
    return refresh_microsoft_access_token(db, conn)


def revoke_microsoft_token(conn: OrganizationEmailConnection) -> None:
    # Microsoft delegated tokens are invalidated by clearing local secrets;
    # optional admin revoke endpoint skipped to avoid extra app permissions.
    return


def send_via_microsoft(
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
    access = ensure_microsoft_access_token(db, conn)
    message: dict = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": to_email}}],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": e}} for e in cc]
    if bcc:
        message["bccRecipients"] = [{"emailAddress": {"address": e}} for e in bcc]
    if reply_to_email:
        message["replyTo"] = [{"emailAddress": {"address": reply_to_email}}]
    if attachments:
        message["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": item.filename,
                "contentType": f"{item.maintype}/{item.subtype}",
                "contentBytes": base64.b64encode(item.content).decode("ascii"),
            }
            for item in attachments
        ]

    response = httpx.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json",
        },
        json={"message": message, "saveToSentItems": True},
        timeout=60.0,
    )
    if response.status_code >= 400:
        if response.status_code in (401, 403):
            mark_connection_error(
                db,
                conn,
                code="revoked",
                message="Connexion Microsoft révoquée. Reconnectez la boîte.",
                status="revoked",
            )
            raise RuntimeError(
                "Votre connexion Microsoft a expiré. Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
            )
        mark_connection_error(
            db, conn, code="provider_error", message="Échec d’envoi Microsoft Graph.", status="error"
        )
        raise RuntimeError("L’e-mail n’a pas pu être envoyé via Microsoft.")

    return SendEmailResult(
        provider="microsoft",
        provider_message_id="",
        sender_email=conn.email_address,
        sender_name=conn.display_name or "",
    )
