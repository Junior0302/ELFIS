from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.models_saas import Organization, OrganizationEmailConnection
from app.services.credential_crypto import encrypt_secret
from app.services.email_connections import (
    get_smtp_password,
    mark_connection_error,
    set_default_connection,
)
from app.services.mailer import MailAttachment, SendEmailResult
from app.services.org_email_settings import org_display_name


def test_smtp_settings(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    security: str,
    from_email: str,
) -> None:
    host = (host or "").strip()
    username = (username or "").strip()
    password = password or ""
    security = (security or "starttls").strip().lower()
    if not host or not from_email:
        raise RuntimeError("Serveur SMTP et adresse d’expédition requis")
    if not password:
        raise RuntimeError("Mot de passe SMTP requis")

    context = ssl.create_default_context()
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port or 465, timeout=25, context=context) as smtp:
            if username:
                smtp.login(username, password)
            smtp.noop()
    else:
        with smtplib.SMTP(host, port or 587, timeout=25) as smtp:
            if security != "none":
                smtp.starttls(context=context)
            if username:
                smtp.login(username, password)
            smtp.noop()


def upsert_custom_smtp(
    db: Session,
    *,
    organization_id: int,
    user_id: int,
    email_address: str,
    display_name: str,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str | None,
    smtp_security: str = "starttls",
    connection_id: int | None = None,
    make_default: bool = False,
    test_before_save: bool = True,
) -> OrganizationEmailConnection:
    email_address = (email_address or "").strip()
    smtp_host = (smtp_host or "").strip()
    smtp_username = (smtp_username or "").strip()
    security = (smtp_security or "starttls").strip().lower()
    if security not in {"starttls", "ssl", "none"}:
        security = "starttls"
    if not email_address or not smtp_host:
        raise RuntimeError("Adresse et serveur SMTP requis")

    conn: OrganizationEmailConnection | None = None
    if connection_id:
        conn = (
            db.query(OrganizationEmailConnection)
            .filter(
                OrganizationEmailConnection.id == connection_id,
                OrganizationEmailConnection.organization_id == organization_id,
                OrganizationEmailConnection.provider == "custom_smtp",
            )
            .first()
        )
    password = smtp_password
    if conn and (password is None or password == ""):
        password = get_smtp_password(conn)
    if not password:
        raise RuntimeError("Mot de passe SMTP requis")

    if test_before_save:
        test_smtp_settings(
            host=smtp_host,
            port=smtp_port or 587,
            username=smtp_username or email_address,
            password=password,
            security=security,
            from_email=email_address,
        )

    org = db.get(Organization, organization_id)
    if not conn:
        conn = OrganizationEmailConnection(
            organization_id=organization_id,
            provider="custom_smtp",
            connected_by_user_id=user_id,
            is_default=False,
        )
        db.add(conn)
        db.flush()

    conn.email_address = email_address
    conn.display_name = (display_name or "").strip() or org_display_name(org)
    conn.smtp_host = smtp_host
    conn.smtp_port = int(smtp_port or 587)
    conn.smtp_username = smtp_username or email_address
    conn.smtp_security = security
    if smtp_password:
        conn.encrypted_smtp_password = encrypt_secret(smtp_password)
    conn.status = "connected"
    conn.last_error_code = ""
    conn.last_error_message = ""
    conn.connected_by_user_id = user_id
    db.add(conn)
    db.commit()
    db.refresh(conn)
    if make_default:
        return set_default_connection(db, organization_id, conn.id)
    return conn


def send_via_org_smtp(
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
    password = get_smtp_password(conn)
    if not password or not conn.smtp_host:
        mark_connection_error(
            db, conn, code="smtp_incomplete", message="Configuration SMTP incomplète.", status="error"
        )
        raise RuntimeError("Configuration SMTP incomplète. Reconfigurez la boîte.")

    msg = EmailMessage()
    from_name = conn.display_name or ""
    from_email = conn.email_address
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to_email
    if reply_to_email:
        msg["Reply-To"] = reply_to_email
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(body)
    for item in attachments or []:
        msg.add_attachment(
            item.content,
            maintype=item.maintype,
            subtype=item.subtype,
            filename=item.filename,
        )
    recipients = [to_email, *(cc or []), *(bcc or [])]
    security = (conn.smtp_security or "starttls").lower()
    context = ssl.create_default_context()
    try:
        if security == "ssl":
            with smtplib.SMTP_SSL(
                conn.smtp_host, conn.smtp_port or 465, timeout=30, context=context
            ) as smtp:
                smtp.login(conn.smtp_username or from_email, password)
                smtp.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(conn.smtp_host, conn.smtp_port or 587, timeout=30) as smtp:
                if security != "none":
                    smtp.starttls(context=context)
                smtp.login(conn.smtp_username or from_email, password)
                smtp.send_message(msg, to_addrs=recipients)
    except Exception as exc:  # noqa: BLE001
        mark_connection_error(
            db,
            conn,
            code="smtp_error",
            message="Échec SMTP. Vérifiez serveur, port et mot de passe d’application.",
            status="error",
        )
        raise RuntimeError(
            "Échec d’envoi SMTP. Reconnectez / reconfigurez la boîte ou choisissez ComptaPilot."
        ) from exc

    return SendEmailResult(
        provider="custom_smtp",
        sender_email=from_email,
        sender_name=from_name,
    )
