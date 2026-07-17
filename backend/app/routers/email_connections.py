from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import Organization
from app.services.auth import write_audit
from app.services.email_connections import (
    activate_platform,
    disconnect_connection,
    ensure_platform_connection,
    get_connection_for_org,
    list_connections,
    list_sendable_connections,
    parse_oauth_state,
    serialize_connection,
    set_default_connection,
)
from app.services.email_dispatch import dispatch_email
from app.services.email_oauth_google import (
    build_google_authorize_url,
    complete_google_oauth,
    google_oauth_configured,
    revoke_google_token,
)
from app.services.email_oauth_microsoft import (
    build_microsoft_authorize_url,
    complete_microsoft_oauth,
    microsoft_oauth_configured,
)
from app.services.email_smtp_org import test_smtp_settings, upsert_custom_smtp
from app.services.mailer import email_configured

router = APIRouter(prefix="/email-connections", tags=["email-connections"])


class SmtpUpsertIn(BaseModel):
    email_address: str
    display_name: str = ""
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str | None = None
    smtp_security: str = "starttls"
    connection_id: int | None = None
    make_default: bool = True


class SmtpTestIn(BaseModel):
    email_address: str
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_security: str = "starttls"


class ConnectionTestIn(BaseModel):
    to_email: str = Field(default="")


def _frontend_redirect(status: str, provider: str, detail: str = "") -> RedirectResponse:
    base = settings.frontend_url.rstrip("/")
    # Settings route in app
    q = f"email_oauth={status}&provider={provider}"
    if detail:
        q += f"&detail={detail[:120]}"
    return RedirectResponse(url=f"{base}/settings?{q}", status_code=302)


@router.get("")
def get_connections(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.view")
    org_id = auth.require_organization_id()
    ensure_platform_connection(db, org_id, connected_by=auth.user.id if auth.user else None)
    rows = list_connections(db, org_id)
    return {
        "connections": [serialize_connection(r) for r in rows],
        "sendable": [serialize_connection(r) for r in list_sendable_connections(db, org_id)],
        "platform_configured": email_configured(),
        "google_oauth_configured": google_oauth_configured(),
        "microsoft_oauth_configured": microsoft_oauth_configured(),
        "can_manage": "*" in auth.permissions or "email_accounts.manage" in auth.permissions,
    }


@router.get("/sendable")
def get_sendable(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.send_email")
    org_id = auth.require_organization_id()
    rows = list_sendable_connections(db, org_id)
    default = next((r for r in rows if r.is_default), rows[0] if rows else None)
    return {
        "connections": [serialize_connection(r) for r in rows],
        "default_connection_id": default.id if default else None,
        "platform_configured": email_configured(),
    }


@router.post("/platform/activate")
def platform_activate(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    if not email_configured():
        raise HTTPException(400, detail="Service ComptaPilot indisponible (BREVO / SMTP plateforme)")
    conn = activate_platform(db, org_id, user_id=auth.user.id if auth.user else None)
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action="email_connection.platform_activate",
        module="email",
    )
    return {"connection": serialize_connection(conn)}


@router.post("/google/start")
def google_start(
    connection_id: int | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        url = build_google_authorize_url(
            organization_id=org_id,
            user_id=auth.user.id,
            connection_id=connection_id,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {"redirect_url": url, "provider": "google"}


@router.get("/oauth/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect("error", "google", error)
    if not code or not state:
        return _frontend_redirect("error", "google", "missing_code")
    try:
        payload = parse_oauth_state(state)
        if payload.get("provider") != "google":
            raise RuntimeError("State OAuth invalide")
        complete_google_oauth(
            db,
            organization_id=int(payload["org_id"]),
            user_id=int(payload["uid"]),
            code=code,
            connection_id=payload.get("cid"),
        )
        write_audit(
            db,
            user_id=int(payload["uid"]),
            organization_id=int(payload["org_id"]),
            action="email_connection.google_connect",
            module="email",
        )
        return _frontend_redirect("success", "google")
    except Exception:  # noqa: BLE001 — ne pas fuiter les détails OAuth
        return _frontend_redirect("error", "google", "oauth_failed")


@router.post("/microsoft/start")
def microsoft_start(
    connection_id: int | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        url = build_microsoft_authorize_url(
            organization_id=org_id,
            user_id=auth.user.id,
            connection_id=connection_id,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {"redirect_url": url, "provider": "microsoft"}


@router.get("/oauth/microsoft/callback")
def microsoft_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect("error", "microsoft", error_description or error)
    if not code or not state:
        return _frontend_redirect("error", "microsoft", "missing_code")
    try:
        payload = parse_oauth_state(state)
        if payload.get("provider") != "microsoft":
            raise RuntimeError("State OAuth invalide")
        complete_microsoft_oauth(
            db,
            organization_id=int(payload["org_id"]),
            user_id=int(payload["uid"]),
            code=code,
            connection_id=payload.get("cid"),
        )
        write_audit(
            db,
            user_id=int(payload["uid"]),
            organization_id=int(payload["org_id"]),
            action="email_connection.microsoft_connect",
            module="email",
        )
        return _frontend_redirect("success", "microsoft")
    except Exception:  # noqa: BLE001
        return _frontend_redirect("error", "microsoft", "oauth_failed")


@router.post("/custom-smtp")
def custom_smtp_upsert(
    payload: SmtpUpsertIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        conn = upsert_custom_smtp(
            db,
            organization_id=org_id,
            user_id=auth.user.id,
            email_address=payload.email_address,
            display_name=payload.display_name,
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port,
            smtp_username=payload.smtp_username,
            smtp_password=payload.smtp_password,
            smtp_security=payload.smtp_security,
            connection_id=payload.connection_id,
            make_default=payload.make_default,
            test_before_save=True,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=org_id,
        action="email_connection.smtp_upsert",
        module="email",
    )
    return {"connection": serialize_connection(conn)}


@router.post("/custom-smtp/test")
def custom_smtp_test(
    payload: SmtpTestIn,
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require("email_accounts.manage")
    try:
        test_smtp_settings(
            host=payload.smtp_host,
            port=payload.smtp_port,
            username=payload.smtp_username or payload.email_address,
            password=payload.smtp_password,
            security=payload.smtp_security,
            from_email=payload.email_address,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {"ok": True, "message": "Connexion SMTP réussie"}


@router.post("/{connection_id}/set-default")
def connection_set_default(
    connection_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    try:
        conn = set_default_connection(db, org_id, connection_id)
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {"connection": serialize_connection(conn)}


@router.post("/{connection_id}/disconnect")
def connection_disconnect(
    connection_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    conn = get_connection_for_org(db, org_id, connection_id)
    if not conn:
        raise HTTPException(404, detail="Connexion introuvable")
    if conn.provider == "google":
        revoke_google_token(conn)
    try:
        conn = disconnect_connection(db, org_id, connection_id)
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action="email_connection.disconnect",
        module="email",
    )
    return {"connection": serialize_connection(conn)}


@router.post("/{connection_id}/reconnect")
def connection_reconnect(
    connection_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    conn = get_connection_for_org(db, org_id, connection_id)
    if not conn:
        raise HTTPException(404, detail="Connexion introuvable")
    if conn.provider == "google":
        url = build_google_authorize_url(
            organization_id=org_id, user_id=auth.user.id, connection_id=connection_id
        )
        return {"redirect_url": url, "provider": "google"}
    if conn.provider == "microsoft":
        url = build_microsoft_authorize_url(
            organization_id=org_id, user_id=auth.user.id, connection_id=connection_id
        )
        return {"redirect_url": url, "provider": "microsoft"}
    if conn.provider == "platform":
        activated = activate_platform(db, org_id, user_id=auth.user.id)
        return {"connection": serialize_connection(activated)}
    raise HTTPException(
        400,
        detail="Pour le SMTP, mettez à jour la configuration depuis Paramètres.",
    )


@router.post("/{connection_id}/test")
def connection_test(
    connection_id: int,
    payload: ConnectionTestIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("email_accounts.manage")
    org_id = auth.require_organization_id()
    conn = get_connection_for_org(db, org_id, connection_id)
    if not conn:
        raise HTTPException(404, detail="Connexion introuvable")
    to_email = (payload.to_email or (auth.user.email if auth.user else "")).strip()
    if not to_email:
        raise HTTPException(400, detail="Adresse de test manquante")
    org = db.get(Organization, org_id)
    try:
        result = dispatch_email(
            db,
            conn,
            organization=org,
            to_email=to_email,
            subject=f"[TEST] Connexion {conn.provider} — ComptaPilot",
            body=(
                f"Test d’envoi depuis {conn.display_name} <{conn.email_address}>.\n"
                f"Fournisseur : {conn.provider}\n"
            ),
            reply_to_email=(org.email if org else None) or None,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {
        "ok": True,
        "provider": result.provider,
        "sender_email": result.sender_email,
        "sender_name": result.sender_name,
        # message id only — never tokens
        "provider_message_id": result.provider_message_id,
    }
