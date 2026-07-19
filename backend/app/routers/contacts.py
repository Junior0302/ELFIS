from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models import Invoice
from app.models_saas import Contact, ContactSuggestion
from app.services.auth import write_audit
from app.services.contacts.creation_service import (
    create_contact_from_document,
    serialize_contact,
    update_contact,
)
from app.services.contacts.detection_service import (
    generate_suggestions,
    list_pending_suggestions,
    resolve_suggestion,
)
from app.services.contacts.enrichment_service import enrich_contact_from_document
from app.services.contacts.errors import ContactError
from app.services.contacts.linking_service import get_org_contact, link_document_to_contact

router = APIRouter(tags=["contacts"], dependencies=[Depends(require_active_subscription)])


class ConfirmedContactData(BaseModel):
    company_name: str | None = None
    trade_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    siren: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = "France"
    iban: str | None = None
    bic: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None


class CreateFromDocumentIn(BaseModel):
    document_id: int
    role: str = "supplier"
    contact_type: str = "supplier"
    suggestion_id: int | None = None
    confirmed_data: ConfirmedContactData


class LinkContactIn(BaseModel):
    contact_id: int
    role: str = "supplier"
    suggestion_id: int | None = None


class IgnoreSuggestionIn(BaseModel):
    role: str = "supplier"
    suggestion_id: int | None = None


class EnrichFromDocumentIn(BaseModel):
    document_id: int
    accepted_fields: list[str] = Field(default_factory=list)
    field_values: dict = Field(default_factory=dict)
    suggestion_id: int | None = None
    confirm_iban: bool = False


class ContactPatchIn(BaseModel):
    contact_type: str | None = None
    status: str | None = None
    company_name: str | None = None
    trade_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    siren: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    iban: str | None = None
    bic: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None
    allow_iban_replace: bool = False


def _http_from_contact_error(exc: ContactError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _org_document(db: Session, document_id: int, organization_id: int) -> Invoice:
    doc = (
        db.query(Invoice)
        .filter(Invoice.id == document_id, Invoice.organization_id == organization_id)
        .first()
    )
    if not doc:
        raise HTTPException(404, detail="Document introuvable")
    return doc


@router.get("/documents/{document_id}/contact-suggestions")
def get_contact_suggestions(
    document_id: int,
    refresh: bool = Query(False),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    org_id = auth.require_organization_id()
    document = _org_document(db, document_id, org_id)
    try:
        if refresh:
            suggestions = generate_suggestions(db, invoice=document, persist=True)
        else:
            suggestions = list_pending_suggestions(
                db, document_id=document.id, organization_id=org_id
            )
            if not suggestions:
                suggestions = generate_suggestions(db, invoice=document, persist=True)
    except ContactError as exc:
        raise _http_from_contact_error(exc) from exc
    return {
        "document_id": document.id,
        "supplier_contact_id": document.supplier_contact_id,
        "customer_contact_id": document.customer_contact_id,
        "suggestions": suggestions,
    }


@router.post("/contacts/from-document")
def create_contact_from_doc(
    payload: CreateFromDocumentIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    org_id = auth.require_organization_id()
    document = _org_document(db, payload.document_id, org_id)
    suggestion = None
    if payload.suggestion_id:
        suggestion = (
            db.query(ContactSuggestion)
            .filter(
                ContactSuggestion.id == payload.suggestion_id,
                ContactSuggestion.organization_id == org_id,
                ContactSuggestion.document_id == document.id,
            )
            .first()
        )
    try:
        contact = create_contact_from_document(
            db,
            organization_id=org_id,
            user_id=auth.user.id if auth.user else None,
            document=document,
            role=payload.role,
            contact_type=payload.contact_type,
            confirmed_data=payload.confirmed_data.model_dump(),
            suggestion=suggestion,
            confidence=suggestion.confidence if suggestion else None,
        )
    except ContactError as exc:
        raise _http_from_contact_error(exc) from exc
    db.refresh(document)
    return {
        "ok": True,
        "contact": serialize_contact(contact),
        "document_id": document.id,
        "supplier_contact_id": document.supplier_contact_id,
        "customer_contact_id": document.customer_contact_id,
    }


@router.post("/documents/{document_id}/link-contact")
def link_contact(
    document_id: int,
    payload: LinkContactIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.write")
    org_id = auth.require_organization_id()
    document = _org_document(db, document_id, org_id)
    try:
        contact = get_org_contact(db, payload.contact_id, org_id)
        suggestion = None
        if payload.suggestion_id:
            suggestion = (
                db.query(ContactSuggestion)
                .filter(
                    ContactSuggestion.id == payload.suggestion_id,
                    ContactSuggestion.organization_id == org_id,
                )
                .first()
            )
        document = link_document_to_contact(
            db,
            document=document,
            contact=contact,
            role=payload.role,
            organization_id=org_id,
            user_id=auth.user.id if auth.user else None,
            suggestion=suggestion,
        )
    except ContactError as exc:
        raise _http_from_contact_error(exc) from exc
    return {
        "ok": True,
        "document_id": document.id,
        "contact": serialize_contact(contact),
        "supplier_contact_id": document.supplier_contact_id,
        "customer_contact_id": document.customer_contact_id,
    }


@router.post("/documents/{document_id}/contact-suggestions/ignore")
def ignore_suggestion(
    document_id: int,
    payload: IgnoreSuggestionIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.write")
    org_id = auth.require_organization_id()
    _org_document(db, document_id, org_id)
    query = db.query(ContactSuggestion).filter(
        ContactSuggestion.document_id == document_id,
        ContactSuggestion.organization_id == org_id,
        ContactSuggestion.status == "pending",
    )
    if payload.suggestion_id:
        query = query.filter(ContactSuggestion.id == payload.suggestion_id)
    else:
        query = query.filter(ContactSuggestion.role == payload.role)
    rows = query.all()
    if not rows:
        raise HTTPException(404, detail="Suggestion introuvable")
    for row in rows:
        resolve_suggestion(
            db,
            suggestion=row,
            status="ignored",
            user_id=auth.user.id if auth.user else None,
        )
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org_id,
        action=f"contact_suggestion_ignored:doc:{document_id}:{payload.role}",
        module="contacts",
    )
    return {"ok": True, "ignored_count": len(rows)}


@router.post("/contacts/{contact_id}/enrich-from-document")
def enrich_contact(
    contact_id: int,
    payload: EnrichFromDocumentIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.write")
    org_id = auth.require_organization_id()
    document = _org_document(db, payload.document_id, org_id)
    try:
        contact = get_org_contact(db, contact_id, org_id)
        suggestion = None
        if payload.suggestion_id:
            suggestion = (
                db.query(ContactSuggestion)
                .filter(
                    ContactSuggestion.id == payload.suggestion_id,
                    ContactSuggestion.organization_id == org_id,
                )
                .first()
            )
        contact = enrich_contact_from_document(
            db,
            contact=contact,
            document=document,
            accepted_fields=payload.accepted_fields,
            field_values=payload.field_values,
            organization_id=org_id,
            user_id=auth.user.id if auth.user else None,
            suggestion=suggestion,
            confirm_iban=payload.confirm_iban,
        )
    except ContactError as exc:
        raise _http_from_contact_error(exc) from exc
    return {"ok": True, "contact": serialize_contact(contact)}


@router.get("/contacts")
def list_contacts(
    contact_type: str | None = None,
    q: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    org_id = auth.require_organization_id()
    query = db.query(Contact).filter(Contact.organization_id == org_id)
    if contact_type:
        query = query.filter(Contact.contact_type == contact_type)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Contact.company_name.ilike(like))
    rows = query.order_by(Contact.company_name.asc()).limit(200).all()
    return {"contacts": [serialize_contact(c) for c in rows]}


@router.get("/contacts/{contact_id}")
def get_contact(
    contact_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    org_id = auth.require_organization_id()
    try:
        contact = get_org_contact(db, contact_id, org_id)
    except ContactError as exc:
        raise _http_from_contact_error(exc) from exc
    return {"contact": serialize_contact(contact)}


@router.patch("/contacts/{contact_id}")
def patch_contact(
    contact_id: int,
    payload: ContactPatchIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.create")
    org_id = auth.require_organization_id()
    try:
        contact = get_org_contact(db, contact_id, org_id)
        data = payload.model_dump(exclude_unset=True)
        allow = bool(data.pop("allow_iban_replace", False))
        contact = update_contact(
            db,
            contact=contact,
            payload=data,
            user_id=auth.user.id if auth.user else None,
            allow_iban_replace=allow,
        )
    except ContactError as exc:
        raise _http_from_contact_error(exc) from exc
    return {"ok": True, "contact": serialize_contact(contact)}
