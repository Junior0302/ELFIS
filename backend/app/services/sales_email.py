from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models_saas import DocumentEmailLog, Organization, SalesDocument, User
from app.services.email_connections import ensure_platform_connection
from app.services.email_dispatch import dispatch_email, resolve_send_connection
from app.services.mailer import MailAttachment, email_configured
from app.services.org_email_settings import (
    build_subject_and_body,
    get_or_create_email_settings,
    is_valid_email,
    org_display_name,
    pdf_filename,
    resolve_sender,
)
from app.services.plan_features import can_send_document_email
from app.services.sales_pdf import sales_document_to_pdf


def smtp_configured() -> bool:
    """Alias rétrocompatible : e-mail transactionnel plateforme prêt."""
    return email_configured()


def _user_facing_error(exc: Exception) -> tuple[str, str]:
    msg = str(exc)
    lower = msg.lower()
    if "adresse e-mail destinataire manquante" in lower or lower.strip() == "missing recipient":
        return "missing_recipient", "Ajoutez une adresse e-mail au client avant l’envoi."
    if "pdf" in lower and ("indisponible" in lower or "génér" in lower or "volumineux" in lower):
        return "pdf_error", "Le document PDF n’a pas pu être généré. Veuillez réessayer."
    if "reconnectez" in lower or "expiré" in lower or "révoqué" in lower:
        return "connection_expired", msg[:280]
    if "introuvable" in lower and "boîte" in lower:
        return "connection_missing", msg[:280]
    if "535" in lower or "auth smtp" in lower:
        return (
            "smtp_auth_failed",
            "Authentification SMTP Brevo refusée (535). "
            "Sur Render : SMTP_USER = login …@smtp-brevo.com, "
            "SMTP_PASSWORD = clé xsmtpsib-…, ou renseignez BREVO_API_KEY (xkeysib-…).",
        )
    if "key not found" in lower or "clé brevo invalide" in lower:
        return (
            "brevo_key_invalid",
            "Clé API Brevo invalide. Sur Render, mettez à jour BREVO_API_KEY "
            "(SMTP & API → API Keys, préfixe xkeysib-…).",
        )
    if "sender" in lower and (
        "not verified" in lower or "invalid" in lower or "unrecognised" in lower or "unauthorized" in lower
    ):
        return (
            "sender_not_verified",
            "L’expéditeur PLATFORM_EMAIL_FROM n’est pas validé dans Brevo. "
            "Utilisez contact@elfis-core.com (ou un expéditeur vérifié) dans Render.",
        )
    if "brevo a refusé" in lower:
        # Extraire le détail court entre parenthèses si présent
        detail = ""
        start = msg.find("(")
        end = msg.find(")", start + 1) if start >= 0 else -1
        if 0 <= start < end and end - start < 120:
            detail = msg[start + 1 : end].strip()
        return (
            "brevo_refused",
            (
                f"Brevo a refusé l’envoi ({detail}). "
                if detail
                else "Brevo a refusé l’envoi. "
            )
            + "Vérifiez BREVO_API_KEY et PLATFORM_EMAIL_FROM sur Render.",
        )
    if "indisponible" in lower or "non configuré" in lower:
        return "platform_unavailable", (
            "Le service d’envoi est temporairement indisponible. "
            "Vérifiez SMTP/Brevo sur Render."
        )
    if "réponse" in lower or ("reply" in lower and "to" in lower and "manqu" in lower):
        return "missing_reply_to", "Ajoutez l’adresse e-mail de votre entreprise dans Paramètres → Entreprise."
    short = msg.strip().replace("\n", " ")
    if len(short) > 240:
        short = short[:237] + "…"
    return "provider_error", short or (
        "L’e-mail n’a pas pu être envoyé. Aucun message n’a été remis au destinataire."
    )


def send_sales_document_email(
    db: Session,
    doc: SalesDocument,
    *,
    recipient: str,
    message: str = "",
    subject: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
    sent_by_user_id: int | None = None,
    is_test: bool = False,
    idempotency_key: str | None = None,
    connection_id: int | None = None,
    preferred_from_email: str | None = None,
    preferred_from_label: str | None = None,
) -> DocumentEmailLog:
    organization = db.get(Organization, doc.organization_id)
    if not organization:
        raise RuntimeError("Organisation introuvable")

    ensure_platform_connection(db, doc.organization_id, connected_by=sent_by_user_id)
    settings_row = get_or_create_email_settings(db, organization)
    platform_sender = resolve_sender(organization, settings_row)
    to_email = (recipient or doc.customer_email or "").strip()
    mail_subject, body = build_subject_and_body(
        doc, organization, settings_row, subject=subject, message=message
    )
    if is_test:
        mail_subject = f"[TEST] {mail_subject}"

    cc_email = (cc if cc is not None else settings_row.cc_email or "").strip()
    bcc_parts: list[str] = []
    if bcc is not None:
        if bcc.strip():
            bcc_parts.append(bcc.strip())
    elif settings_row.bcc_email.strip():
        bcc_parts.append(settings_row.bcc_email.strip())
    if settings_row.send_copy_to_organization and is_valid_email(organization.email or ""):
        org_mail = organization.email.strip()
        if org_mail.lower() not in {to_email.lower(), *(p.lower() for p in bcc_parts), cc_email.lower()}:
            bcc_parts.append(org_mail)
    bcc_email = ", ".join(dict.fromkeys(bcc_parts))

    key = (idempotency_key or "").strip()
    if not key:
        raw = (
            f"{doc.organization_id}:{doc.id}:{to_email}:{mail_subject}:"
            f"{is_test}:{connection_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        )
        key = hashlib.sha256(raw.encode()).hexdigest()[:48]

    recent = (
        db.query(DocumentEmailLog)
        .filter(
            DocumentEmailLog.organization_id == doc.organization_id,
            DocumentEmailLog.idempotency_key == key,
            DocumentEmailLog.status.in_(("preparing", "queued", "sent", "delivered", "opened")),
            DocumentEmailLog.sent_at >= datetime.utcnow() - timedelta(minutes=2),
        )
        .first()
    )
    if recent:
        return recent

    log = DocumentEmailLog(
        sales_document_id=doc.id,
        organization_id=doc.organization_id,
        document_type=doc.doc_type,
        sent_by_user_id=sent_by_user_id,
        recipient=to_email,
        recipient_email=to_email,
        cc_email=cc_email,
        bcc_email=bcc_email,
        sender_name="",
        sender_email="",
        reply_to_email=platform_sender.reply_to_email,
        subject=mail_subject,
        provider="",
        provider_message_id="",
        email_connection_id=connection_id,
        idempotency_key=key,
        status="preparing",
        error_code="",
        error_message="",
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    if not to_email or not is_valid_email(to_email):
        log.status = "failed"
        log.error_code = "missing_recipient"
        log.error_message = "Ajoutez une adresse e-mail au client avant l’envoi."
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    try:
        conn = resolve_send_connection(db, doc.organization_id, connection_id)
    except RuntimeError as exc:
        code, message = _user_facing_error(exc)
        log.status = "failed"
        log.error_code = code
        log.error_message = message
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    log.email_connection_id = conn.id
    # Expéditeur affiché = From plateforme (ou boîte connectée), pas l’e-mail perso Reply-To
    log.sender_name = (
        (
            preferred_from_label
            if preferred_from_email and preferred_from_email.lower().endswith("@elfis-core.com")
            else ""
        )
        or conn.display_name
        or platform_sender.sender_name
        or ""
    ).strip()
    log.sender_email = (
        (
            preferred_from_email
            if preferred_from_email and preferred_from_email.lower().endswith("@elfis-core.com")
            else ""
        )
        or conn.email_address
        or platform_sender.sender_email
        or ""
    ).strip()
    if preferred_from_email and is_valid_email(preferred_from_email.strip()):
        log.reply_to_email = preferred_from_email.strip()
    elif conn.provider == "platform":
        log.reply_to_email = platform_sender.reply_to_email
        if not is_valid_email(platform_sender.reply_to_email):
            log.status = "failed"
            log.error_code = "missing_reply_to"
            log.error_message = (
                "Ajoutez l’adresse e-mail de votre entreprise dans Paramètres → Entreprise."
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
    else:
        log.reply_to_email = conn.email_address or platform_sender.reply_to_email

    recipient_count = 1 + (1 if cc_email and is_valid_email(cc_email) else 0)
    allowed, limit_code = can_send_document_email(
        db, doc.organization_id, recipient_count=max(1, recipient_count)
    )
    if not allowed:
        log.status = "blocked"
        log.error_code = limit_code
        if limit_code == "email_monthly_limit":
            log.error_message = (
                "La limite mensuelle d’e-mails de votre organisation est atteinte."
            )
        elif limit_code == "email_recipient_limit":
            log.error_message = (
                "Trop de destinataires pour votre abonnement. Réduisez CC/BCC."
            )
        else:
            log.error_message = "L’envoi d’e-mails n’est pas inclus dans votre abonnement."
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    try:
        pdf_bytes = sales_document_to_pdf(doc, organization)
        if not pdf_bytes or len(pdf_bytes) < 20:
            raise RuntimeError("PDF indisponible")
        if len(pdf_bytes) > 14 * 1024 * 1024:
            raise RuntimeError("PDF trop volumineux")

        # Adresse ELFIS Core (@elfis-core.com) : From réel via Brevo si validée.
        # Adresse personnelle : Reply-To uniquement (Brevo ne peut pas usurper Gmail/Outlook).
        platform_from_email: str | None = None
        platform_from_name: str | None = None
        preferred = (preferred_from_email or "").strip()
        if (
            conn.provider == "platform"
            and preferred
            and is_valid_email(preferred)
            and preferred.lower().endswith("@elfis-core.com")
        ):
            platform_from_email = preferred
            platform_from_name = (preferred_from_label or "").strip() or preferred

        result = dispatch_email(
            db,
            conn,
            organization=organization,
            to_email=to_email,
            subject=mail_subject,
            body=body,
            attachments=[
                MailAttachment(
                    filename=pdf_filename(doc, organization),
                    content=pdf_bytes,
                    maintype="application",
                    subtype="pdf",
                )
            ],
            reply_to_email=log.reply_to_email or None,
            reply_to_name=(
                preferred_from_label
                or (platform_sender.reply_to_name if conn.provider == "platform" else None)
            ),
            sender_email=platform_from_email,
            sender_name=platform_from_name,
            cc=[cc_email] if cc_email and is_valid_email(cc_email) else None,
            bcc=[e for e in bcc_parts if is_valid_email(e)],
        )
        log.status = "sent"
        log.provider = result.provider
        log.provider_message_id = result.provider_message_id
        log.sender_email = result.sender_email
        log.sender_name = result.sender_name
        log.error_code = ""
        log.error_message = ""
        log.sent_at = datetime.utcnow()
        if not is_test and doc.status == "draft":
            doc.status = "sent"
            if doc.doc_type == "devis":
                doc.signature_status = "pending"
            db.add(doc)
    except Exception as exc:  # noqa: BLE001
        code, message = _user_facing_error(exc)
        log.status = "failed"
        log.error_code = code
        log.error_message = message

    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def log_mailto_document_send(
    db: Session,
    doc: SalesDocument,
    *,
    recipient: str,
    message: str = "",
    subject: str | None = None,
    sent_by_user: User | None,
    idempotency_key: str | None = None,
    preferred_from_email: str | None = None,
    preferred_from_label: str | None = None,
) -> DocumentEmailLog:
    """Enregistre un envoi via la messagerie de l’utilisateur (sans SMTP serveur)."""
    organization = db.get(Organization, doc.organization_id)
    if not organization:
        raise RuntimeError("Organisation introuvable")

    settings_row = get_or_create_email_settings(db, organization)
    to_email = (recipient or doc.customer_email or "").strip()
    mail_subject, body = build_subject_and_body(
        doc, organization, settings_row, subject=subject, message=message
    )

    sender_email = (preferred_from_email or "").strip()
    sender_name = (preferred_from_label or "").strip() or org_display_name(organization)
    if not sender_email and sent_by_user and (sent_by_user.email or "").strip():
        sender_email = sent_by_user.email.strip()
        full = f"{(sent_by_user.first_name or '').strip()} {(sent_by_user.last_name or '').strip()}".strip()
        if full:
            sender_name = full
    if not sender_email:
        sender_email = (organization.email or settings_row.reply_to_email or "").strip()
    if not sender_email or not is_valid_email(sender_email):
        raise RuntimeError(
            "Aucune adresse d’expéditeur. Renseignez votre e-mail de compte ou celui de l’entreprise."
        )
    if not to_email or not is_valid_email(to_email):
        raise RuntimeError("Ajoutez une adresse e-mail au client avant l’envoi.")

    key = (idempotency_key or "").strip()
    if not key:
        raw = f"mailto:{doc.organization_id}:{doc.id}:{to_email}:{mail_subject}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        key = hashlib.sha256(raw.encode()).hexdigest()[:48]

    recent = (
        db.query(DocumentEmailLog)
        .filter(
            DocumentEmailLog.organization_id == doc.organization_id,
            DocumentEmailLog.idempotency_key == key,
            DocumentEmailLog.status.in_(("preparing", "queued", "sent", "delivered", "opened")),
            DocumentEmailLog.sent_at >= datetime.utcnow() - timedelta(minutes=2),
        )
        .first()
    )
    if recent:
        return recent

    log = DocumentEmailLog(
        sales_document_id=doc.id,
        organization_id=doc.organization_id,
        document_type=doc.doc_type,
        sent_by_user_id=sent_by_user.id if sent_by_user else None,
        recipient=to_email,
        recipient_email=to_email,
        sender_name=sender_name,
        sender_email=sender_email,
        reply_to_email=sender_email,
        subject=mail_subject,
        provider="mailto",
        provider_message_id="",
        idempotency_key=key,
        status="sent",
        error_code="",
        error_message="Ouvert dans la messagerie de l’utilisateur — PDF à joindre manuellement.",
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    if doc.status == "draft":
        doc.status = "sent"
        if doc.doc_type == "devis":
            doc.signature_status = "pending"
        db.add(doc)
    db.commit()
    db.refresh(log)
    return log


def send_organization_test_email(
    db: Session,
    organization: Organization,
    *,
    to_email: str,
    sent_by_user: User | None,
    connection_id: int | None = None,
) -> DocumentEmailLog:
    """Envoie un e-mail de test (sans PDF document)."""
    ensure_platform_connection(
        db, organization.id, connected_by=sent_by_user.id if sent_by_user else None
    )
    settings_row = get_or_create_email_settings(db, organization)
    platform_sender = resolve_sender(organization, settings_row)
    recipient = (to_email or "").strip()
    if not is_valid_email(recipient):
        raise RuntimeError("Adresse e-mail de test invalide")

    conn = resolve_send_connection(db, organization.id, connection_id)
    org_name = org_display_name(organization)
    subject = f"[TEST] Envoi ComptaPilot — {org_name}"
    body = (
        f"Bonjour,\n\n"
        f"Ceci est un e-mail de test pour l’organisation {org_name}.\n\n"
        f"Expéditeur : {conn.display_name} <{conn.email_address}>\n"
        f"Fournisseur : {conn.provider}\n\n"
        f"Cordialement,\n{org_name}"
    )
    reply = (
        platform_sender.reply_to_email
        if conn.provider == "platform"
        else (conn.email_address or platform_sender.reply_to_email)
    )
    result = dispatch_email(
        db,
        conn,
        organization=organization,
        to_email=recipient,
        subject=subject,
        body=body,
        reply_to_email=reply or None,
        reply_to_name=platform_sender.reply_to_name if conn.provider == "platform" else None,
    )
    log = DocumentEmailLog(
        sales_document_id=None,
        organization_id=organization.id,
        document_type="test",
        sent_by_user_id=sent_by_user.id if sent_by_user else None,
        recipient=recipient,
        recipient_email=recipient,
        sender_name=result.sender_name,
        sender_email=result.sender_email,
        reply_to_email=reply or "",
        subject=subject,
        provider=result.provider,
        provider_message_id=result.provider_message_id,
        email_connection_id=conn.id,
        status="sent",
        sent_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
