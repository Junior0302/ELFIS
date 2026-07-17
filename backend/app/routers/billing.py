from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import (
    CatalogItem,
    CommercialActivity,
    Customer,
    Organization,
    Payment,
    Reminder,
    SalesDocument,
)
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


class CustomerUpdateIn(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    vat_number: str | None = None


class CatalogItemIn(BaseModel):
    name: str
    kind: str = "produit"
    unit: str = "unité"
    unit_price_ht: float = 0.0
    vat_rate: float = 20.0
    active: bool = True


class CatalogItemUpdateIn(BaseModel):
    name: str | None = None
    kind: str | None = None
    unit: str | None = None
    unit_price_ht: float | None = None
    vat_rate: float | None = None
    active: bool | None = None


class ActivityIn(BaseModel):
    title: str
    kind: str = "rdv"
    customer_id: int | None = None
    scheduled_at: str | None = None
    status: str = "planifie"
    notes: str = ""


class ActivityUpdateIn(BaseModel):
    title: str | None = None
    kind: str | None = None
    customer_id: int | None = None
    scheduled_at: str | None = None
    status: str | None = None
    notes: str | None = None


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
    cc: str | None = None
    bcc: str | None = None
    is_test: bool = False
    idempotency_key: str | None = None
    connection_id: int | None = None
    # mailto = ouverture messagerie utilisateur (sans SMTP) ; server = Brevo/OAuth
    send_mode: str = "mailto"
    sender_acknowledged: bool = False
    # Expéditeur choisi (ELFIS pro / perso) — utilisé pour Reply-To et journal
    preferred_from_email: str | None = None
    preferred_from_label: str | None = None


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


def _serialize_email_log(log, db: Session | None = None) -> dict:
    sent_by_email = ""
    sent_by_name = ""
    uid = getattr(log, "sent_by_user_id", None)
    if db is not None and uid:
        from app.models_saas import User

        user = db.get(User, uid)
        if user:
            sent_by_email = user.email or ""
            sent_by_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or (
                user.email or ""
            )
    return {
        "id": log.id,
        "sales_document_id": log.sales_document_id,
        "organization_id": getattr(log, "organization_id", None),
        "document_type": getattr(log, "document_type", "") or "",
        "sent_by_user_id": uid,
        "sent_by_email": sent_by_email,
        "sent_by_name": sent_by_name,
        "recipient": log.recipient or getattr(log, "recipient_email", "") or "",
        "recipient_email": getattr(log, "recipient_email", None) or log.recipient or "",
        "cc_email": getattr(log, "cc_email", "") or "",
        "bcc_email": getattr(log, "bcc_email", "") or "",
        "sender_name": getattr(log, "sender_name", "") or "",
        "sender_email": getattr(log, "sender_email", "") or "",
        "reply_to_email": getattr(log, "reply_to_email", "") or "",
        "subject": log.subject,
        "provider": getattr(log, "provider", "") or "",
        "provider_message_id": getattr(log, "provider_message_id", "") or "",
        "status": log.status,
        "error_code": getattr(log, "error_code", "") or "",
        "error_message": log.error_message or "",
        "sent_at": log.sent_at,
        "delivered_at": getattr(log, "delivered_at", None),
        "opened_at": getattr(log, "opened_at", None),
        "bounced_at": getattr(log, "bounced_at", None),
        "updated_at": getattr(log, "updated_at", None),
    }


def _serialize_customer(c: Customer) -> dict:
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "name": c.name,
        "email": c.email or "",
        "phone": c.phone or "",
        "address": c.address or "",
        "vat_number": c.vat_number or "",
        "created_at": c.created_at,
    }


def _serialize_catalog(item: CatalogItem) -> dict:
    return {
        "id": item.id,
        "organization_id": item.organization_id,
        "name": item.name,
        "kind": item.kind,
        "unit": item.unit,
        "unit_price_ht": item.unit_price_ht,
        "vat_rate": item.vat_rate,
        "active": item.active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _parse_scheduled_at(value: str | None):
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(400, detail="Date/heure invalide (ISO attendu)") from exc


def _serialize_activity(act: CommercialActivity, customer_name: str = "") -> dict:
    return {
        "id": act.id,
        "organization_id": act.organization_id,
        "title": act.title,
        "kind": act.kind,
        "customer_id": act.customer_id,
        "customer_name": customer_name,
        "scheduled_at": act.scheduled_at.isoformat() if act.scheduled_at else None,
        "status": act.status,
        "notes": act.notes or "",
        "created_at": act.created_at,
        "updated_at": act.updated_at,
    }


def _get_customer(db: Session, auth: AuthContext, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer or customer.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Client introuvable")
    return customer


def _get_catalog_item(db: Session, auth: AuthContext, item_id: int) -> CatalogItem:
    item = db.get(CatalogItem, item_id)
    if not item or item.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Article introuvable")
    return item


def _get_activity(db: Session, auth: AuthContext, activity_id: int) -> CommercialActivity:
    act = db.get(CommercialActivity, activity_id)
    if not act or act.organization_id != _org_id(auth):
        raise HTTPException(404, detail="Activité introuvable")
    return act


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


@router.get("/customers")
def list_customers(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    q: str | None = None,
):
    auth.require("invoice.read")
    org_id = _org_id(auth)
    query = db.query(Customer).filter(Customer.organization_id == org_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Customer.name.ilike(like))
            | (Customer.email.ilike(like))
            | (Customer.phone.ilike(like))
        )
    customers = query.order_by(Customer.name.asc()).all()
    return {"customers": [_serialize_customer(c) for c in customers]}


@router.post("/customers")
def create_customer(
    payload: CustomerIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    org_id = _org_id(auth)
    if not payload.name.strip():
        raise HTTPException(400, detail="Nom requis")
    customer = Customer(organization_id=org_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action=f"create_customer:{customer.id}",
        module="facturation",
    )
    return _serialize_customer(customer)


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    return _serialize_customer(_get_customer(db, auth, customer_id))


@router.patch("/customers/{customer_id}")
def update_customer(
    customer_id: int,
    payload: CustomerUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    customer = _get_customer(db, auth, customer_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and not str(data["name"] or "").strip():
        raise HTTPException(400, detail="Nom requis")
    for key, value in data.items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return _serialize_customer(customer)


@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    customer = _get_customer(db, auth, customer_id)
    db.delete(customer)
    db.commit()
    return {"ok": True}


@router.get("/catalog")
def list_catalog(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    active_only: bool = False,
):
    auth.require("invoice.read")
    org_id = _org_id(auth)
    query = db.query(CatalogItem).filter(CatalogItem.organization_id == org_id)
    if active_only:
        query = query.filter(CatalogItem.active.is_(True))
    items = query.order_by(CatalogItem.name.asc()).all()
    return {"items": [_serialize_catalog(i) for i in items]}


@router.post("/catalog")
def create_catalog_item(
    payload: CatalogItemIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    if payload.kind not in ("produit", "service"):
        raise HTTPException(400, detail="Type invalide (produit|service)")
    if not payload.name.strip():
        raise HTTPException(400, detail="Nom requis")
    item = CatalogItem(organization_id=_org_id(auth), **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_catalog(item)


@router.patch("/catalog/{item_id}")
def update_catalog_item(
    item_id: int,
    payload: CatalogItemUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    item = _get_catalog_item(db, auth, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "kind" in data and data["kind"] not in ("produit", "service"):
        raise HTTPException(400, detail="Type invalide (produit|service)")
    if "name" in data and not str(data["name"] or "").strip():
        raise HTTPException(400, detail="Nom requis")
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return _serialize_catalog(item)


@router.delete("/catalog/{item_id}")
def delete_catalog_item(
    item_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    item = _get_catalog_item(db, auth, item_id)
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/activities")
def list_activities(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    status: str | None = None,
    kind: str | None = None,
):
    auth.require("invoice.read")
    org_id = _org_id(auth)
    query = db.query(CommercialActivity).filter(CommercialActivity.organization_id == org_id)
    if status:
        query = query.filter(CommercialActivity.status == status.strip().lower())
    if kind:
        query = query.filter(CommercialActivity.kind == kind.strip().lower())
    activities = query.order_by(CommercialActivity.id.desc()).all()
    customer_ids = {a.customer_id for a in activities if a.customer_id}
    names: dict[int, str] = {}
    if customer_ids:
        for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all():
            names[c.id] = c.name
    return {
        "activities": [
            _serialize_activity(a, names.get(a.customer_id or 0, "")) for a in activities
        ]
    }


@router.post("/activities")
def create_activity(
    payload: ActivityIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    if payload.kind not in ("vente", "service", "rdv", "suivi"):
        raise HTTPException(400, detail="Type invalide")
    if payload.status not in ("planifie", "fait", "annule"):
        raise HTTPException(400, detail="Statut invalide")
    if not payload.title.strip():
        raise HTTPException(400, detail="Titre requis")
    org_id = _org_id(auth)
    if payload.customer_id is not None:
        _get_customer(db, auth, payload.customer_id)
    act = CommercialActivity(
        organization_id=org_id,
        title=payload.title.strip(),
        kind=payload.kind,
        customer_id=payload.customer_id,
        scheduled_at=_parse_scheduled_at(payload.scheduled_at),
        status=payload.status,
        notes=payload.notes or "",
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    name = ""
    if act.customer_id:
        c = db.get(Customer, act.customer_id)
        name = c.name if c else ""
    return _serialize_activity(act, name)


@router.patch("/activities/{activity_id}")
def update_activity(
    activity_id: int,
    payload: ActivityUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    act = _get_activity(db, auth, activity_id)
    data = payload.model_dump(exclude_unset=True)
    if "kind" in data and data["kind"] not in ("vente", "service", "rdv", "suivi"):
        raise HTTPException(400, detail="Type invalide")
    if "status" in data and data["status"] not in ("planifie", "fait", "annule"):
        raise HTTPException(400, detail="Statut invalide")
    if "title" in data and not str(data["title"] or "").strip():
        raise HTTPException(400, detail="Titre requis")
    if "customer_id" in data and data["customer_id"] is not None:
        _get_customer(db, auth, data["customer_id"])
    if "scheduled_at" in data:
        data["scheduled_at"] = _parse_scheduled_at(data["scheduled_at"])
    for key, value in data.items():
        setattr(act, key, value)
    db.commit()
    db.refresh(act)
    name = ""
    if act.customer_id:
        c = db.get(Customer, act.customer_id)
        name = c.name if c else ""
    return _serialize_activity(act, name)


@router.delete("/activities/{activity_id}")
def delete_activity(
    activity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    act = _get_activity(db, auth, activity_id)
    db.delete(act)
    db.commit()
    return {"ok": True}


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
        "email_logs": [
            _serialize_email_log(log, db)
            for log in list_email_logs(db, doc.id, organization_id=doc.organization_id)
        ],
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
    auth.require("documents.send_email")
    doc = _get_doc(db, auth, doc_id)
    recipient = (payload.recipient or doc.customer_email or "").strip()
    if recipient and recipient != (doc.customer_email or "") and not payload.is_test:
        doc.customer_email = recipient
        db.add(doc)
        db.commit()
        db.refresh(doc)

    mode = (payload.send_mode or "mailto").strip().lower()
    if mode == "mailto":
        from app.services.sales_email import log_mailto_document_send

        if not payload.sender_acknowledged:
            raise HTTPException(
                400,
                detail="Confirmez que l’e-mail partira depuis votre adresse avant d’ouvrir la messagerie.",
            )
        log = log_mailto_document_send(
            db,
            doc,
            recipient=recipient,
            message=payload.message,
            subject=payload.subject,
            sent_by_user=auth.user,
            idempotency_key=payload.idempotency_key,
            preferred_from_email=payload.preferred_from_email,
            preferred_from_label=payload.preferred_from_label,
        )
    else:
        log = send_sales_document_email(
            db,
            doc,
            recipient=recipient,
            message=payload.message,
            subject=payload.subject,
            cc=payload.cc,
            bcc=payload.bcc,
            sent_by_user_id=auth.user.id if auth.user else None,
            is_test=payload.is_test,
            idempotency_key=payload.idempotency_key,
            connection_id=payload.connection_id,
            preferred_from_email=payload.preferred_from_email,
            preferred_from_label=payload.preferred_from_label,
        )
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=_org_id(auth),
        action=f"email_{doc.doc_type}:{doc.number}:{log.status}:{mode}",
        module="facturation",
    )
    return {
        "document": _serialize(doc),
        "email_log": _serialize_email_log(log, db),
        "smtp_configured": smtp_configured(),
        "email_configured": smtp_configured() if mode == "server" else True,
        "send_mode": mode,
        "sender_email": log.sender_email,
        "can_send_direct": smtp_configured(),
    }


@router.get("/documents/{doc_id}/emails")
def document_emails(
    doc_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    # invoice.read OU historique e-mails
    if not (
        "*" in auth.permissions
        or "invoice.read" in auth.permissions
        or "documents.view_email_history" in auth.permissions
        or "documents.send_email" in auth.permissions
    ):
        auth.require("invoice.read")
    doc = _get_doc(db, auth, doc_id)
    from app.services.org_email_settings import (
        get_or_create_email_settings,
        resolve_sender,
        build_subject_and_body,
        pdf_filename,
    )
    from app.services.email_connections import (
        ensure_platform_connection,
        get_default_connection,
        list_sendable_connections,
        serialize_connection,
    )
    from app.models_saas import Organization

    org = db.get(Organization, doc.organization_id)
    preview = None
    connections: list = []
    default_connection_id = None
    if org:
        ensure_platform_connection(db, org.id)
        row = get_or_create_email_settings(db, org)
        sender = resolve_sender(org, row)
        subject, message = build_subject_and_body(doc, org, row)
        sendable = list_sendable_connections(db, org.id)
        connections = [serialize_connection(c) for c in sendable]
        default = get_default_connection(db, org.id)
        default_connection_id = default.id if default and default.status == "connected" else (
            sendable[0].id if sendable else None
        )
        default_conn = next((c for c in sendable if c.id == default_connection_id), None)
        preview = {
            "recipient": doc.customer_email or "",
            "cc": row.cc_email or "",
            "bcc": row.bcc_email or "",
            "subject": subject,
            "message": message,
            "pdf_filename": pdf_filename(doc, org),
            "sender_name": (default_conn.display_name if default_conn else sender.sender_name),
            "sender_email": (default_conn.email_address if default_conn else sender.sender_email),
            "reply_to_email": sender.reply_to_email,
            "sender_mode": (default_conn.provider if default_conn else sender.mode),
            "connection_id": default_connection_id,
            "user_email": (auth.user.email if auth.user else "") or "",
            "org_email": (org.email or "").strip(),
            "preferred_send_mode": "server" if smtp_configured() else "mailto",
        }
    return {
        "email_logs": [
            _serialize_email_log(log, db)
            for log in list_email_logs(db, doc.id, organization_id=doc.organization_id)
        ],
        "smtp_configured": smtp_configured(),
        "email_configured": smtp_configured(),
        "preview": preview,
        "connections": connections,
        "default_connection_id": default_connection_id,
        "can_send_direct": smtp_configured(),
    }


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
