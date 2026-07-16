from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Customer, Payment, Reminder, SalesDocument
from app.services.auth import write_audit
from app.services.billing import (
    convert_quote_to_invoice,
    create_credit_note,
    create_sales_document,
    register_payment,
    send_document,
    send_reminder,
    sign_document,
)

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
    customer_id: int | None = None
    amount_ht: float
    vat_rate: float = 20.0
    notes: str = ""
    lines: list[dict] = Field(default_factory=list)
    due_days: int = 30


class PaymentIn(BaseModel):
    amount: float
    method: str = "virement"
    reference: str = ""


def _org_id(auth: AuthContext) -> int:
    return auth.require_organization_id()


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
    }


@router.get("/overview")
def billing_overview(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    org_id = _org_id(auth)
    docs = (
        db.query(SalesDocument)
        .filter(SalesDocument.organization_id == org_id)
        .order_by(SalesDocument.id.desc())
        .all()
    )
    customers = db.query(Customer).filter(Customer.organization_id == org_id).all()
    unpaid = [d for d in docs if d.doc_type == "facture" and d.status in ("sent", "partial", "overdue")]
    return {
        "module": "Module 4 — Facturation",
        "stats": {
            "documents": len(docs),
            "customers": len(customers),
            "unpaid": len(unpaid),
            "unpaid_amount": round(sum(d.amount_ttc - d.paid_amount for d in unpaid), 2),
            "quotes": sum(1 for d in docs if d.doc_type == "devis"),
            "invoices": sum(1 for d in docs if d.doc_type == "facture"),
            "credits": sum(1 for d in docs if d.doc_type == "avoir"),
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


@router.post("/documents/{doc_id}/send")
def send_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
    return _serialize(send_document(db, doc))


@router.post("/documents/{doc_id}/convert")
def convert_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
    try:
        invoice = convert_quote_to_invoice(db, doc)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return _serialize(invoice)


@router.post("/documents/{doc_id}/credit-note")
def credit_note(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
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
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
    payment = register_payment(
        db, doc, amount=payload.amount, method=payload.method, reference=payload.reference
    )
    return {
        "payment_id": payment.id,
        "document": _serialize(doc),
    }


@router.post("/documents/{doc_id}/remind")
def remind_doc(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.create")
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
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
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
    return _serialize(sign_document(db, doc))


@router.get("/documents/{doc_id}/payments")
def list_payments(doc_id: int, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require("invoice.read")
    doc = db.get(SalesDocument, doc_id)
    if not doc or doc.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Document introuvable")
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
