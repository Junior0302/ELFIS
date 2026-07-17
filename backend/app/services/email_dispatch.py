from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_saas import Organization, OrganizationEmailConnection
from app.services.email_connections import (
    get_connection_for_org,
    get_default_connection,
    mark_connection_used,
)
from app.services.email_oauth_google import send_via_gmail
from app.services.email_oauth_microsoft import send_via_microsoft
from app.services.email_smtp_org import send_via_org_smtp
from app.services.mailer import MailAttachment, SendEmailResult, email_configured, send_email
from app.services.org_email_settings import org_display_name


def resolve_send_connection(
    db: Session,
    organization_id: int,
    connection_id: int | None,
) -> OrganizationEmailConnection:
    if connection_id is not None:
        conn = get_connection_for_org(db, organization_id, connection_id)
        if not conn or conn.status == "disconnected":
            raise RuntimeError("Boîte d’expédition introuvable pour cette organisation.")
    else:
        conn = get_default_connection(db, organization_id)
        if not conn:
            raise RuntimeError("Aucune boîte d’expédition configurée.")

    if conn.status != "connected":
        provider_label = {
            "google": "Google",
            "microsoft": "Microsoft",
            "custom_smtp": "SMTP",
            "platform": "ComptaPilot",
        }.get(conn.provider, conn.provider)
        raise RuntimeError(
            f"Votre connexion {provider_label} a expiré. "
            "Reconnectez votre boîte ou choisissez l’envoi via ComptaPilot."
        )
    return conn


def dispatch_email(
    db: Session,
    conn: OrganizationEmailConnection,
    *,
    organization: Organization | None,
    to_email: str,
    subject: str,
    body: str,
    attachments: list[MailAttachment] | None = None,
    reply_to_email: str | None = None,
    reply_to_name: str | None = None,
    sender_email: str | None = None,
    sender_name: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> SendEmailResult:
    """Envoie via le fournisseur de la connexion — jamais de fallback silencieux."""
    if conn.provider == "platform":
        if not email_configured():
            raise RuntimeError("Le service d’envoi ComptaPilot est temporairement indisponible.")
        result = send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            attachments=attachments,
            sender_name=sender_name or conn.display_name or org_display_name(organization),
            sender_email=sender_email or conn.email_address or None,
            reply_to_email=reply_to_email,
            reply_to_name=reply_to_name,
            cc=cc,
            bcc=bcc,
        )
        mark_connection_used(db, conn)
        return result

    if conn.provider == "google":
        result = send_via_gmail(
            db,
            conn,
            to_email=to_email,
            subject=subject,
            body=body,
            attachments=attachments,
            reply_to_email=reply_to_email,
            cc=cc,
            bcc=bcc,
        )
        mark_connection_used(db, conn)
        return result

    if conn.provider == "microsoft":
        result = send_via_microsoft(
            db,
            conn,
            to_email=to_email,
            subject=subject,
            body=body,
            attachments=attachments,
            reply_to_email=reply_to_email,
            cc=cc,
            bcc=bcc,
        )
        mark_connection_used(db, conn)
        return result

    if conn.provider == "custom_smtp":
        result = send_via_org_smtp(
            db,
            conn,
            to_email=to_email,
            subject=subject,
            body=body,
            attachments=attachments,
            reply_to_email=reply_to_email,
            cc=cc,
            bcc=bcc,
        )
        mark_connection_used(db, conn)
        return result

    raise RuntimeError(f"Fournisseur d’envoi inconnu: {conn.provider}")
