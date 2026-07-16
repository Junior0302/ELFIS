from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models_saas import Customer, DocumentEmailLog, Payment, Reminder, SalesDocument


def _next_number(db: Session, org_id: int, doc_type: str) -> str:
    prefix = {"devis": "DEV", "facture": "FAC", "avoir": "AVO"}.get(doc_type, "DOC")
    year = datetime.utcnow().year
    count = (
        db.query(SalesDocument)
        .filter(
            SalesDocument.organization_id == org_id,
            SalesDocument.doc_type == doc_type,
        )
        .count()
        + 1
    )
    return f"{prefix}-{year}-{count:04d}"


def create_sales_document(
    db: Session,
    *,
    organization_id: int,
    doc_type: str,
    customer_name: str,
    amount_ht: float,
    vat_rate: float = 20.0,
    customer_id: int | None = None,
    customer_email: str = "",
    lines: list[dict] | None = None,
    notes: str = "",
    due_days: int = 30,
) -> SalesDocument:
    email = (customer_email or "").strip()
    if customer_id and not email:
        customer = db.get(Customer, customer_id)
        if customer and customer.organization_id == organization_id:
            email = customer.email or ""
    tva = round(amount_ht * vat_rate / 100.0, 2)
    ttc = round(amount_ht + tva, 2)
    today = datetime.utcnow().date()
    due = today + timedelta(days=due_days)
    doc = SalesDocument(
        organization_id=organization_id,
        customer_id=customer_id,
        doc_type=doc_type,
        number=_next_number(db, organization_id, doc_type),
        issue_date=today.strftime("%d-%m-%Y"),
        due_date=due.strftime("%d-%m-%Y"),
        status="draft",
        customer_name=customer_name,
        customer_email=email,
        amount_ht=amount_ht,
        amount_tva=tva,
        amount_ttc=ttc,
        vat_rate=vat_rate,
        lines_json=json.dumps(lines or [], ensure_ascii=False),
        notes=notes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_sales_document(
    db: Session,
    doc: SalesDocument,
    *,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_id: int | None = None,
    amount_ht: float | None = None,
    vat_rate: float | None = None,
    notes: str | None = None,
    lines: list[dict] | None = None,
    due_days: int | None = None,
) -> SalesDocument:
    if customer_name is not None:
        doc.customer_name = customer_name.strip()
    if customer_email is not None:
        doc.customer_email = customer_email.strip()
    if customer_id is not None:
        doc.customer_id = customer_id
        if not doc.customer_email:
            customer = db.get(Customer, customer_id)
            if customer and customer.organization_id == doc.organization_id:
                doc.customer_email = customer.email or ""
    if vat_rate is not None:
        doc.vat_rate = vat_rate
    if amount_ht is not None:
        doc.amount_ht = amount_ht
    if amount_ht is not None or vat_rate is not None:
        doc.amount_tva = round(doc.amount_ht * doc.vat_rate / 100.0, 2)
        doc.amount_ttc = round(doc.amount_ht + doc.amount_tva, 2)
    if notes is not None:
        doc.notes = notes
    if lines is not None:
        doc.lines_json = json.dumps(lines, ensure_ascii=False)
    if due_days is not None:
        today = datetime.utcnow().date()
        doc.due_date = (today + timedelta(days=due_days)).strftime("%d-%m-%Y")
    doc.updated_at = datetime.utcnow()
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_sales_document(db: Session, doc: SalesDocument) -> None:
    db.query(Payment).filter(Payment.sales_document_id == doc.id).delete()
    db.query(Reminder).filter(Reminder.sales_document_id == doc.id).delete()
    db.query(DocumentEmailLog).filter(DocumentEmailLog.sales_document_id == doc.id).delete()
    db.delete(doc)
    db.commit()


def send_document(db: Session, doc: SalesDocument) -> SalesDocument:
    doc.status = "sent"
    if doc.doc_type == "devis":
        doc.signature_status = "pending"
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def convert_quote_to_invoice(db: Session, quote: SalesDocument) -> SalesDocument:
    if quote.doc_type != "devis":
        raise ValueError("Seul un devis peut être converti")
    invoice = create_sales_document(
        db,
        organization_id=quote.organization_id,
        doc_type="facture",
        customer_name=quote.customer_name,
        amount_ht=quote.amount_ht,
        vat_rate=quote.vat_rate,
        customer_id=quote.customer_id,
        customer_email=quote.customer_email,
        lines=json.loads(quote.lines_json or "[]"),
        notes=f"Converti depuis {quote.number}",
    )
    invoice.converted_from_id = quote.id
    invoice.status = "sent"
    quote.status = "accepted"
    db.add_all([invoice, quote])
    db.commit()
    db.refresh(invoice)
    return invoice


def create_credit_note(db: Session, invoice: SalesDocument) -> SalesDocument:
    if invoice.doc_type != "facture":
        raise ValueError("Avoir uniquement depuis une facture")
    avoir = create_sales_document(
        db,
        organization_id=invoice.organization_id,
        doc_type="avoir",
        customer_name=invoice.customer_name,
        amount_ht=invoice.amount_ht,
        vat_rate=invoice.vat_rate,
        customer_id=invoice.customer_id,
        customer_email=invoice.customer_email,
        lines=json.loads(invoice.lines_json or "[]"),
        notes=f"Avoir sur {invoice.number}",
    )
    avoir.converted_from_id = invoice.id
    avoir.status = "sent"
    db.add(avoir)
    db.commit()
    db.refresh(avoir)
    return avoir


def register_payment(
    db: Session,
    doc: SalesDocument,
    *,
    amount: float,
    method: str = "virement",
    reference: str = "",
) -> Payment:
    payment = Payment(
        sales_document_id=doc.id,
        amount=amount,
        method=method,
        paid_at=datetime.utcnow().strftime("%d-%m-%Y"),
        reference=reference,
    )
    doc.paid_amount = round((doc.paid_amount or 0) + amount, 2)
    if doc.paid_amount >= doc.amount_ttc - 0.01:
        doc.status = "paid"
    else:
        doc.status = "partial"
    db.add_all([payment, doc])
    db.commit()
    db.refresh(payment)
    return payment


def send_reminder(db: Session, doc: SalesDocument) -> Reminder:
    level = db.query(Reminder).filter(Reminder.sales_document_id == doc.id).count() + 1
    messages = {
        1: f"Rappel amiable : la facture {doc.number} de {doc.amount_ttc:.2f} € est en attente.",
        2: f"2e relance : merci de régulariser la facture {doc.number} sous 8 jours.",
        3: f"Mise en demeure : facture {doc.number} toujours impayée.",
    }
    reminder = Reminder(
        sales_document_id=doc.id,
        level=level,
        channel="email",
        message=messages.get(level, messages[3]),
        status="sent",
    )
    if doc.status not in ("paid", "cancelled"):
        doc.status = "overdue"
    db.add_all([reminder, doc])
    db.commit()
    db.refresh(reminder)
    return reminder


def sign_document(db: Session, doc: SalesDocument) -> SalesDocument:
    doc.signature_status = "signed"
    if doc.doc_type == "devis" and doc.status == "sent":
        doc.status = "accepted"
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_email_logs(db: Session, doc_id: int) -> list[DocumentEmailLog]:
    return (
        db.query(DocumentEmailLog)
        .filter(DocumentEmailLog.sales_document_id == doc_id)
        .order_by(DocumentEmailLog.id.desc())
        .all()
    )
