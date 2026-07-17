from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Organization, OrganizationEmailSettings, SalesDocument
from app.services.mailer import email_configured


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class ResolvedSender:
    mode: str  # platform | custom_sender
    sender_email: str
    sender_name: str
    reply_to_email: str
    reply_to_name: str
    using_custom: bool


def is_valid_email(value: str) -> bool:
    return bool(value and EMAIL_RE.match(value.strip()))


def org_display_name(org: Organization | None) -> str:
    if not org:
        return "ComptaPilot"
    return (org.legal_name or org.name or "Entreprise").strip() or "Entreprise"


def get_or_create_email_settings(db: Session, organization: Organization) -> OrganizationEmailSettings:
    row = (
        db.query(OrganizationEmailSettings)
        .filter(OrganizationEmailSettings.organization_id == organization.id)
        .first()
    )
    if row:
        return row
    name = org_display_name(organization)
    row = OrganizationEmailSettings(
        organization_id=organization.id,
        sender_mode="platform",
        sender_name=name,
        reply_to_email=(organization.email or "").strip(),
        reply_to_name=name,
        send_copy_to_organization=True,
        custom_sender_status="not_configured",
        custom_domain_status="not_configured",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def serialize_email_settings(row: OrganizationEmailSettings, org: Organization) -> dict:
    reply = (row.reply_to_email or org.email or "").strip()
    config_state = "ready" if email_configured() and is_valid_email(reply) else (
        "platform_unavailable" if not email_configured() else "needs_reply_to"
    )
    custom_ok = (
        row.sender_mode == "custom_sender"
        and row.custom_sender_status == "verified"
        and is_valid_email(row.custom_sender_email)
    )
    return {
        "organization_id": row.organization_id,
        "sender_mode": row.sender_mode if custom_ok or row.sender_mode == "platform" else "platform",
        "sender_name": row.sender_name or org_display_name(org),
        "reply_to_email": reply,
        "reply_to_name": row.reply_to_name or org_display_name(org),
        "cc_email": row.cc_email or "",
        "bcc_email": row.bcc_email or "",
        "invoice_default_subject": row.invoice_default_subject or "",
        "invoice_default_message": row.invoice_default_message or "",
        "quote_default_subject": row.quote_default_subject or "",
        "quote_default_message": row.quote_default_message or "",
        "email_signature": row.email_signature or "",
        "send_copy_to_organization": bool(row.send_copy_to_organization),
        "custom_sender_email": row.custom_sender_email or "",
        "custom_sender_status": row.custom_sender_status or "not_configured",
        "custom_domain": row.custom_domain or "",
        "custom_domain_status": row.custom_domain_status or "not_configured",
        "platform_configured": email_configured(),
        "configuration_state": config_state,
        "effective_from_preview": (
            f"{row.sender_name or org_display_name(org)} <{settings.effective_platform_from}>"
            if email_configured()
            else ""
        ),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def upsert_email_settings(
    db: Session,
    organization: Organization,
    payload: dict,
) -> OrganizationEmailSettings:
    row = get_or_create_email_settings(db, organization)
    for field in (
        "sender_mode",
        "sender_name",
        "reply_to_email",
        "reply_to_name",
        "cc_email",
        "bcc_email",
        "invoice_default_subject",
        "invoice_default_message",
        "quote_default_subject",
        "quote_default_message",
        "email_signature",
        "custom_sender_email",
        "custom_domain",
    ):
        if field in payload and payload[field] is not None:
            setattr(row, field, str(payload[field]).strip())
    if "send_copy_to_organization" in payload and payload["send_copy_to_organization"] is not None:
        row.send_copy_to_organization = bool(payload["send_copy_to_organization"])
    if row.sender_mode not in {"platform", "custom_sender"}:
        row.sender_mode = "platform"
    # Custom sender ne s'active que si déjà verified côté backend
    if row.sender_mode == "custom_sender" and row.custom_sender_status != "verified":
        row.sender_mode = "platform"
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def resolve_sender(organization: Organization, row: OrganizationEmailSettings) -> ResolvedSender:
    name = (row.sender_name or org_display_name(organization)).strip()
    reply = (row.reply_to_email or organization.email or "").strip()
    reply_name = (row.reply_to_name or name).strip()
    custom_ok = (
        row.sender_mode == "custom_sender"
        and row.custom_sender_status == "verified"
        and is_valid_email(row.custom_sender_email)
    )
    if custom_ok:
        return ResolvedSender(
            mode="custom_sender",
            sender_email=row.custom_sender_email.strip(),
            sender_name=name,
            reply_to_email=reply or row.custom_sender_email.strip(),
            reply_to_name=reply_name,
            using_custom=True,
        )
    return ResolvedSender(
        mode="platform",
        sender_email=settings.effective_platform_from,
        sender_name=name,
        reply_to_email=reply,
        reply_to_name=reply_name,
        using_custom=False,
    )


def _fmt_amount(value: float) -> str:
    return f"{value:,.2f} €".replace(",", " ").replace(".", ",")


def _replace(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def default_subject(doc: SalesDocument, org: Organization) -> str:
    org_name = org_display_name(org)
    if doc.doc_type == "devis":
        return f"Devis {doc.number} — {org_name}"
    return f"Facture {doc.number} — {org_name}"


def default_body(doc: SalesDocument, org: Organization, signature: str = "") -> str:
    org_name = org_display_name(org)
    customer = (doc.customer_name or "Madame, Monsieur").strip()
    sig = (signature or "").strip()
    if doc.doc_type == "devis":
        text = (
            f"Bonjour {customer},\n\n"
            f"Veuillez trouver en pièce jointe notre devis {doc.number} "
            f"d’un montant de {_fmt_amount(doc.amount_ttc)}.\n\n"
            f"Ce devis est valable jusqu’au :\n{doc.due_date or '—'}\n\n"
            "Vous pouvez répondre directement à cet e-mail pour toute question.\n\n"
            f"Cordialement,\n\n{org_name}"
        )
    else:
        text = (
            f"Bonjour {customer},\n\n"
            f"Veuillez trouver en pièce jointe la facture {doc.number} "
            f"d’un montant de {_fmt_amount(doc.amount_ttc)}.\n\n"
            f"Date d’émission :\n{doc.issue_date or '—'}\n\n"
            f"Date d’échéance :\n{doc.due_date or '—'}\n\n"
            "Vous pouvez répondre directement à cet e-mail pour toute question.\n\n"
            f"Cordialement,\n\n{org_name}"
        )
    if sig:
        text = f"{text}\n{sig}"
    return text


def build_subject_and_body(
    doc: SalesDocument,
    org: Organization,
    row: OrganizationEmailSettings,
    *,
    subject: str | None = None,
    message: str | None = None,
) -> tuple[str, str]:
    mapping = {
        "invoice_number": doc.number,
        "quote_number": doc.number,
        "organization_name": org_display_name(org),
        "customer_name": doc.customer_name or "Madame, Monsieur",
        "total_ttc": _fmt_amount(doc.amount_ttc),
        "issue_date": doc.issue_date or "—",
        "due_date": doc.due_date or "—",
        "valid_until": doc.due_date or "—",
        "email_signature": row.email_signature or "",
    }
    if subject and subject.strip():
        mail_subject = subject.strip()
    elif doc.doc_type == "devis" and row.quote_default_subject.strip():
        mail_subject = _replace(row.quote_default_subject, mapping)
    elif doc.doc_type != "devis" and row.invoice_default_subject.strip():
        mail_subject = _replace(row.invoice_default_subject, mapping)
    else:
        mail_subject = default_subject(doc, org)

    if message and message.strip():
        body = message.strip()
        if row.email_signature.strip() and row.email_signature.strip() not in body:
            body = f"{body}\n\n{row.email_signature.strip()}"
    elif doc.doc_type == "devis" and row.quote_default_message.strip():
        body = _replace(row.quote_default_message, mapping)
    elif doc.doc_type != "devis" and row.invoice_default_message.strip():
        body = _replace(row.invoice_default_message, mapping)
    else:
        body = default_body(doc, org, row.email_signature)
    return mail_subject, body


def pdf_filename(doc: SalesDocument, org: Organization) -> str:
    label = "Devis" if doc.doc_type == "devis" else "Facture"
    org_slug = re.sub(r"[^A-Za-z0-9]+", "-", org_display_name(org)).strip("-") or "ORG"
    return f"{label}-{doc.number}-{org_slug}.pdf"
