from __future__ import annotations

import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import DocumentEmailLog, Organization, SalesDocument
from app.services.sales_pdf import sales_document_to_pdf


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def _doc_label(doc: SalesDocument) -> str:
    return {"devis": "Devis", "facture": "Facture", "avoir": "Avoir"}.get(doc.doc_type, "Document")


def send_sales_document_email(
    db: Session,
    doc: SalesDocument,
    *,
    recipient: str,
    message: str = "",
    subject: str | None = None,
) -> DocumentEmailLog:
    to_email = (recipient or doc.customer_email or "").strip()
    label = _doc_label(doc)
    mail_subject = subject or f"{label} n°{doc.number}"
    body = (
        message.strip()
        or (
            f"Bonjour,\n\nVeuillez trouver ci-joint votre {label.lower()} {doc.number}.\n\n"
            f"Montant TTC : {doc.amount_ttc:.2f} €.\n\nCordialement,\nComptaPilot IA"
        )
    )

    log = DocumentEmailLog(
        sales_document_id=doc.id,
        organization_id=doc.organization_id,
        recipient=to_email,
        subject=mail_subject,
        status="pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    if not to_email:
        log.status = "failed"
        log.error_message = "Adresse e-mail destinataire manquante"
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    if not smtp_configured():
        log.status = "failed"
        log.error_message = (
            "SMTP non configuré (SMTP_HOST / SMTP_FROM). "
            "Le PDF peut être téléchargé, mais l’e-mail n’a pas été envoyé."
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    organization = db.get(Organization, doc.organization_id)
    pdf_bytes = sales_document_to_pdf(doc, organization)
    msg = EmailMessage()
    msg["Subject"] = mail_subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(body)
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"{doc.number}.pdf",
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        log.status = "sent"
        log.error_message = ""
        if doc.status == "draft":
            doc.status = "sent"
            if doc.doc_type == "devis":
                doc.signature_status = "pending"
            db.add(doc)
    except Exception as exc:  # noqa: BLE001 — journaliser l'échec d'envoi
        log.status = "failed"
        log.error_message = str(exc)[:400]

    db.add(log)
    db.commit()
    db.refresh(log)
    return log
