from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Customer, Organization, Payment, Reminder, SalesDocument
from app.services.auth import write_audit
from app.services.billing import (
    convert_quote_to_invoice,
    create_credit_note,
    create_sales_document,
    delete_sales_document,
    list_email_logs,
    register_payment,
    send_document,
    send_reminder,
    sign_document,
    update_sales_document,
)
from app.services.sales_email import send_sales_document_email, smtp_configured
from app.services.sales_pdf import sales_document_to_pdf

router = APIRouter(
    prefix="/billing",
    tags=["facturation"],
    dependencies=[Depends(require_active_subscription)],
)


class CustomerIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""
    vat_number: str = ""


class SalesDocIn(BaseModel):
    doc_type: str = "facture"
    customer_name: str
    customer_email: str = ""
    customer_id: int | None = None
    amount_ht: float
    vat_rate: float = 20.0
    notes: str = ""
    lines: list[dict] = Field(default_factory=list)
    due_days: int = 30


class SalesDocUpdateIn(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    customer_id: int | None = None
    amount_ht: float | None = None
    vat_rate: float | None = None
    notes: str | None = None
    lines: list[dict] | None = None
    due_days: int | None = None


class PaymentIn(BaseModel):
    amount: float
    method: str = "virement"
    reference: str = ""


class EmailSendIn(BaseModel):
    recipient: str = ""
    message: str = ""
    subject: str | None = None


def _org_id(auth: AuthContext) -> int:
    return auth.require_organization_id()


def _get_doc(db: Session, auth: AuthContext, doc_id: int) -> SalesDocument:
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
    return doc


def _serialize(doc: SalesDocument) -> dict:
    return {
        "id": doc.id,
        "organization_id": doc.organization_id,
        "customer_id": doc.customer_id,
        "doc_type": doc.doc_type,
        "number": doc.number,
        "issue_date": doc.issue_date,
        "due_date": doc.due_date,
        "status": doc.status,
        "customer_name": doc.customer_name,
        "customer_email": doc.customer_email or "",
        "amount_ht": doc.amount_ht,
        "amount_tva": doc.amount_tva,
        "amount_ttc": doc.amount_ttc,
        "vat_rate": doc.vat_rate,
        "lines": json.loads(doc.lines_json or "[]"),
        "notes": doc.notes,
        "paid_amount": doc.paid_amount,
        "signature_status": doc.signature_status,
        "converted_from_id": doc.converted_from_id,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


def _serialize_email_log(log) -> dict:
    return {
        "id": log.id,
        "sales_document_id": log.sales_document_id,
        "recipient": log.recipient,
        "subject": log.subject,
        "status": log.status,
        "error_message": log.error_message,
        "sent_at": log.sent_at,
    }


@router.get("/overview")
def billing_overview(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    doc_type: str | None = None,
    q: str | None = None,
    status: str | None = None,
):
    auth.require("invoice.read")
    org_id = _org_id(auth)
    query = db.query(SalesDocument).filter(SalesDocument.organization_id == org_id)
    if doc_type in {"devis", "facture", "avoir"}:
        query = query.filter(SalesDocument.doc_type == doc_type)
    if status:
        query = query.filter(SalesDocument.status == status.strip().lower())
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (SalesDocument.number.ilike(like))
            | (SalesDocument.customer_name.ilike(like))
            | (SalesDocument.customer_email.ilike(like))
        )
    docs = query.order_by(SalesDocument.id.desc()).all()
    all_docs = (
        db.query(SalesDocument)
        .filter(SalesDocument.organization_id == org_id)
        .all()
    )
    customers = db.query(Customer).filter(Customer.organization_id == org_id).all()
    unpaid = [
        d for d in all_docs if d.doc_type == "facture" and d.status in ("sent", "partial", "overdue")
    ]
    return {
        "module": "Module 4 — Facturation",
        "smtp_configured": smtp_configured(),
        "stats": {
            "documents": len(all_docs),
            "customers": len(customers),
            "unpaid": len(unpaid),
            "unpaid_amount": round(sum(d.amount_ttc - d.paid_amount for d in unpaid), 2),
            "quotes": sum(1 for d in all_docs if d.doc_type == "devis"),
            "invoices": sum(1 for d in all_docs if d.doc_type == "facture"),
            "credits": sum(1 for d in all_docs if d.doc_type == "avoir"),
        },
        "documents": [_serialize(d) for d in docs],
        "customers": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "address": c.address,
            }
            for c in customers
        ],
    }


@router.post("/customers")
def create_customer(
    payload: CustomerIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    org_id = _org_id(auth)
    customer = Customer(organization_id=org_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"id": customer.id, "name": customer.name, "email": customer.email}


@router.post("/documents")
def create_document(
    payload: SalesDocIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    perm = "quote.create" if payload.doc_type == "devis" else "invoice.create"
    auth.require(perm)
    if payload.doc_type not in ("devis", "facture", "avoir"):
        raise HTTPException(400, detail="Type invalide")
    doc = create_sales_document(
        db,
        organization_id=_org_id(auth),
        doc_type=payload.doc_type,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        amount_ht=payload.amount_ht,
        vat_rate=payload.vat_rate,
        customer_id=payload.customer_id,
        lines=payload.lines,
        notes=payload.notes,
        due_days=payload.due_days,
    )
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=_org_id(auth),
        action=f"create_{payload.doc_type}:{doc.number}",
        module="facturation",
    )
    return _serialize(doc)


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.read")
    doc = _get_doc(db, auth, doc_id)
    return {
        "document": _serialize(doc),
        "email_logs": [_serialize_email_log(log) for log in list_email_logs(db, doc.id)],
    }


@router.patch("/documents/{doc_id}")
def patch_document(
    doc_id: int,
    payload: SalesDocUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    updated = update_sales_document(db, doc, **payload.model_dump(exclude_unset=True))
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=_org_id(auth),
        action=f"update_{updated.doc_type}:{updated.number}",
        module="facturation",
    )
    return _serialize(updated)


@router.delete("/documents/{doc_id}")
def remove_document(
    doc_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    number = doc.number
    doc_type = doc.doc_type
    delete_sales_document(db, doc)
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=_org_id(auth),
        action=f"delete_{doc_type}:{number}",
        module="facturation",
    )
    return {"ok": True}


@router.get("/documents/{doc_id}/pdf")
def document_pdf(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.read")
    doc = _get_doc(db, auth, doc_id)
    organization = db.get(Organization, doc.organization_id)
    pdf = sales_document_to_pdf(doc, organization)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.number}.pdf"'},
    )


@router.post("/documents/{doc_id}/email")
def email_document(
    doc_id: int,
    payload: EmailSendIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    recipient = (payload.recipient or doc.customer_email or "").strip()
    if recipient and recipient != (doc.customer_email or ""):
        doc.customer_email = recipient
        db.add(doc)
        db.commit()
        db.refresh(doc)
    log = send_sales_document_email(
        db,
        doc,
        recipient=recipient,
        message=payload.message,
        subject=payload.subject,
    )
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=_org_id(auth),
        action=f"email_{doc.doc_type}:{doc.number}:{log.status}",
        module="facturation",
    )
    return {
        "document": _serialize(doc),
        "email_log": _serialize_email_log(log),
        "smtp_configured": smtp_configured(),
    }


@router.get("/documents/{doc_id}/emails")
def document_emails(
    doc_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    doc = _get_doc(db, auth, doc_id)
    return {"email_logs": [_serialize_email_log(log) for log in list_email_logs(db, doc.id)]}


@router.post("/documents/{doc_id}/send")
def send_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    return _serialize(send_document(db, doc))


@router.post("/documents/{doc_id}/convert")
def convert_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    try:
        invoice = convert_quote_to_invoice(db, doc)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return _serialize(invoice)


@router.post("/documents/{doc_id}/credit-note")
def credit_note(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    try:
        avoir = create_credit_note(db, doc)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return _serialize(avoir)


@router.post("/documents/{doc_id}/pay")
def pay_doc(
    doc_id: int,
    payload: PaymentIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    payment = register_payment(
        db, doc, amount=payload.amount, method=payload.method, reference=payload.reference
    )
    return {"payment_id": payment.id, "document": _serialize(doc)}


@router.post("/documents/{doc_id}/remind")
def remind_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    reminder = send_reminder(db, doc)
    return {
        "reminder": {
            "id": reminder.id,
            "level": reminder.level,
            "message": reminder.message,
            "sent_at": reminder.sent_at,
        },
        "document": _serialize(doc),
    }


@router.post("/documents/{doc_id}/sign")
def sign_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = _get_doc(db, auth, doc_id)
    return _serialize(sign_document(db, doc))


@router.get("/documents/{doc_id}/payments")
def list_payments(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.read")
    doc = _get_doc(db, auth, doc_id)
    payments = db.query(Payment).filter(Payment.sales_document_id == doc_id).all()
    reminders = db.query(Reminder).filter(Reminder.sales_document_id == doc_id).all()
    return {
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "method": p.method,
                "paid_at": p.paid_at,
                "reference": p.reference,
            }
            for p in payments
        ],
        "reminders": [
            {
                "id": r.id,
                "level": r.level,
                "message": r.message,
                "sent_at": r.sent_at,
            }
            for r in reminders
        ],
    }
