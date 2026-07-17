from __future__ import annotations

from datetime import datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Organization, OrganizationEmailConnection
from app.services.credential_crypto import decrypt_secret, encrypt_secret
from app.services.mailer import email_configured
from app.services.org_email_settings import org_display_name


PROVIDERS = {"platform", "google", "microsoft", "custom_smtp"}
STATUSES = {"connected", "expired", "revoked", "error", "disconnected"}


def serialize_connection(conn: OrganizationEmailConnection) -> dict:
    """Sérialisation publique — jamais de tokens / mots de passe."""
    return {
        "id": conn.id,
        "organization_id": conn.organization_id,
        "provider": conn.provider,
        "email_address": conn.email_address or "",
        "display_name": conn.display_name or "",
        "status": conn.status,
        "is_default": bool(conn.is_default),
        "connected_by_user_id": conn.connected_by_user_id,
        "provider_account_id": conn.provider_account_id or "",
        "smtp_host": conn.smtp_host or "" if conn.provider == "custom_smtp" else "",
        "smtp_port": conn.smtp_port if conn.provider == "custom_smtp" else None,
        "smtp_username": conn.smtp_username or "" if conn.provider == "custom_smtp" else "",
        "smtp_security": conn.smtp_security if conn.provider == "custom_smtp" else "",
        "has_smtp_password": bool(conn.encrypted_smtp_password),
        "token_expires_at": conn.token_expires_at.isoformat() if conn.token_expires_at else None,
        "last_used_at": conn.last_used_at.isoformat() if conn.last_used_at else None,
        "last_error_code": conn.last_error_code or "",
        "last_error_message": conn.last_error_message or "",
        "created_at": conn.created_at.isoformat() if conn.created_at else None,
        "updated_at": conn.updated_at.isoformat() if conn.updated_at else None,
        "from_preview": _from_preview(conn),
    }


def _from_preview(conn: OrganizationEmailConnection) -> str:
    name = (conn.display_name or "").strip()
    email = (conn.email_address or "").strip()
    if conn.provider == "platform":
        email = email or settings.effective_platform_from
    if name and email:
        return f"{name} <{email}>"
    return email or name or "—"


def list_connections(db: Session, organization_id: int) -> list[OrganizationEmailConnection]:
    ensure_platform_connection(db, organization_id)
    return (
        db.query(OrganizationEmailConnection)
        .filter(OrganizationEmailConnection.organization_id == organization_id)
        .filter(OrganizationEmailConnection.status != "disconnected")
        .order_by(
            OrganizationEmailConnection.is_default.desc(),
            OrganizationEmailConnection.id.asc(),
        )
        .all()
    )


def list_sendable_connections(
    db: Session, organization_id: int
) -> list[OrganizationEmailConnection]:
    """Connexions utilisables comme From (connected uniquement + platform si Brevo OK)."""
    ensure_platform_connection(db, organization_id)
    rows = (
        db.query(OrganizationEmailConnection)
        .filter(OrganizationEmailConnection.organization_id == organization_id)
        .filter(OrganizationEmailConnection.status == "connected")
        .order_by(
            OrganizationEmailConnection.is_default.desc(),
            OrganizationEmailConnection.id.asc(),
        )
        .all()
    )
    out: list[OrganizationEmailConnection] = []
    for row in rows:
        if row.provider == "platform" and not email_configured():
            continue
        out.append(row)
    return out


def get_connection_for_org(
    db: Session, organization_id: int, connection_id: int
) -> OrganizationEmailConnection | None:
    return (
        db.query(OrganizationEmailConnection)
        .filter(
            OrganizationEmailConnection.id == connection_id,
            OrganizationEmailConnection.organization_id == organization_id,
        )
        .first()
    )


def get_default_connection(
    db: Session, organization_id: int
) -> OrganizationEmailConnection | None:
    ensure_platform_connection(db, organization_id)
    row = (
        db.query(OrganizationEmailConnection)
        .filter(
            OrganizationEmailConnection.organization_id == organization_id,
            OrganizationEmailConnection.is_default.is_(True),
            OrganizationEmailConnection.status == "connected",
        )
        .first()
    )
    if row:
        return row
    return (
        db.query(OrganizationEmailConnection)
        .filter(
            OrganizationEmailConnection.organization_id == organization_id,
            OrganizationEmailConnection.provider == "platform",
            OrganizationEmailConnection.status == "connected",
        )
        .first()
    )


def ensure_platform_connection(
    db: Session, organization_id: int, *, connected_by: int | None = None
) -> OrganizationEmailConnection:
    org = db.get(Organization, organization_id)
    existing = (
        db.query(OrganizationEmailConnection)
        .filter(
            OrganizationEmailConnection.organization_id == organization_id,
            OrganizationEmailConnection.provider == "platform",
        )
        .first()
    )
    name = org_display_name(org)
    from_email = settings.effective_platform_from
    if existing:
        if not existing.email_address and from_email:
            existing.email_address = from_email
        if not existing.display_name:
            existing.display_name = name
        if existing.status == "disconnected":
            existing.status = "connected"
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    has_default = (
        db.query(OrganizationEmailConnection)
        .filter(
            OrganizationEmailConnection.organization_id == organization_id,
            OrganizationEmailConnection.is_default.is_(True),
        )
        .first()
        is not None
    )
    row = OrganizationEmailConnection(
        organization_id=organization_id,
        provider="platform",
        email_address=from_email,
        display_name=name,
        status="connected",
        is_default=not has_default,
        connected_by_user_id=connected_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_default_connection(
    db: Session, organization_id: int, connection_id: int
) -> OrganizationEmailConnection:
    conn = get_connection_for_org(db, organization_id, connection_id)
    if not conn or conn.status == "disconnected":
        raise RuntimeError("Connexion introuvable")
    if conn.status != "connected":
        raise RuntimeError(
            "Reconnectez cette boîte avant de l’utiliser comme expéditeur par défaut."
        )
    others = (
        db.query(OrganizationEmailConnection)
        .filter(
            OrganizationEmailConnection.organization_id == organization_id,
            OrganizationEmailConnection.id != conn.id,
        )
        .all()
    )
    for other in others:
        if other.is_default:
            other.is_default = False
            db.add(other)
    conn.is_default = True
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def activate_platform(
    db: Session, organization_id: int, *, user_id: int | None = None
) -> OrganizationEmailConnection:
    conn = ensure_platform_connection(db, organization_id, connected_by=user_id)
    conn.status = "connected"
    conn.last_error_code = ""
    conn.last_error_message = ""
    db.add(conn)
    db.commit()
    return set_default_connection(db, organization_id, conn.id)


def mark_connection_error(
    db: Session,
    conn: OrganizationEmailConnection,
    *,
    code: str,
    message: str,
    status: str = "error",
) -> None:
    conn.status = status if status in STATUSES else "error"
    conn.last_error_code = (code or "")[:64]
    # Message utilisateur uniquement — jamais de secrets
    conn.last_error_message = (message or "")[:400]
    conn.updated_at = datetime.utcnow()
    db.add(conn)
    db.commit()


def mark_connection_used(db: Session, conn: OrganizationEmailConnection) -> None:
    conn.last_used_at = datetime.utcnow()
    conn.last_error_code = ""
    conn.last_error_message = ""
    if conn.status in {"error", "expired"} and conn.provider == "platform":
        conn.status = "connected"
    db.add(conn)
    db.commit()


def store_oauth_tokens(
    conn: OrganizationEmailConnection,
    *,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    email: str,
    display_name: str,
    provider_account_id: str = "",
) -> None:
    conn.encrypted_access_token = encrypt_secret(access_token)
    if refresh_token:
        conn.encrypted_refresh_token = encrypt_secret(refresh_token)
    if expires_in:
        conn.token_expires_at = datetime.utcnow() + timedelta(seconds=max(60, int(expires_in) - 60))
    conn.email_address = (email or "").strip()
    if display_name:
        conn.display_name = display_name.strip()
    if provider_account_id:
        conn.provider_account_id = provider_account_id.strip()
    conn.status = "connected"
    conn.last_error_code = ""
    conn.last_error_message = ""
    conn.updated_at = datetime.utcnow()


def clear_secrets(conn: OrganizationEmailConnection) -> None:
    conn.encrypted_access_token = ""
    conn.encrypted_refresh_token = ""
    conn.encrypted_smtp_password = ""
    conn.token_expires_at = None


def disconnect_connection(
    db: Session, organization_id: int, connection_id: int
) -> OrganizationEmailConnection:
    conn = get_connection_for_org(db, organization_id, connection_id)
    if not conn:
        raise RuntimeError("Connexion introuvable")
    if conn.provider == "platform":
        raise RuntimeError("Le mode ComptaPilot ne peut pas être déconnecté — activez-le comme défaut.")
    was_default = bool(conn.is_default)
    clear_secrets(conn)
    conn.status = "disconnected"
    conn.is_default = False
    conn.updated_at = datetime.utcnow()
    db.add(conn)
    db.commit()
    if was_default:
        activate_platform(db, organization_id)
    db.refresh(conn)
    return conn


def get_access_token(conn: OrganizationEmailConnection) -> str:
    return decrypt_secret(conn.encrypted_access_token)


def get_refresh_token(conn: OrganizationEmailConnection) -> str:
    return decrypt_secret(conn.encrypted_refresh_token)


def get_smtp_password(conn: OrganizationEmailConnection) -> str:
    return decrypt_secret(conn.encrypted_smtp_password)


def create_oauth_state(
    *,
    organization_id: int,
    user_id: int,
    provider: str,
    connection_id: int | None = None,
) -> str:
    payload = {
        "org_id": organization_id,
        "uid": user_id,
        "provider": provider,
        "cid": connection_id,
        "exp": datetime.utcnow() + timedelta(minutes=10),
        "purpose": "email_oauth",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def parse_oauth_state(state: str) -> dict:
    try:
        data = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise RuntimeError("State OAuth invalide ou expiré") from exc
    if data.get("purpose") != "email_oauth":
        raise RuntimeError("State OAuth invalide")
    return data


def upsert_provider_connection(
    db: Session,
    *,
    organization_id: int,
    provider: str,
    user_id: int,
    email: str,
    display_name: str,
    access_token: str,
    refresh_token: str | None,
    expires_in: int | None,
    provider_account_id: str = "",
    connection_id: int | None = None,
    make_default: bool = True,
) -> OrganizationEmailConnection:
    conn: OrganizationEmailConnection | None = None
    if connection_id:
        conn = get_connection_for_org(db, organization_id, connection_id)
    if not conn:
        conn = (
            db.query(OrganizationEmailConnection)
            .filter(
                OrganizationEmailConnection.organization_id == organization_id,
                OrganizationEmailConnection.provider == provider,
                OrganizationEmailConnection.email_address == email,
            )
            .first()
        )
    if not conn:
        conn = OrganizationEmailConnection(
            organization_id=organization_id,
            provider=provider,
            connected_by_user_id=user_id,
            is_default=False,
        )
        db.add(conn)
        db.flush()

    store_oauth_tokens(
        conn,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        email=email,
        display_name=display_name or org_display_name(db.get(Organization, organization_id)),
        provider_account_id=provider_account_id,
    )
    conn.connected_by_user_id = user_id
    db.add(conn)
    db.commit()
    db.refresh(conn)
    if make_default:
        return set_default_connection(db, organization_id, conn.id)
    return conn
