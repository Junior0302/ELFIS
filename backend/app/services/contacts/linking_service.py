from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Invoice
from app.models_saas import Contact, ContactSuggestion
from app.services.auth import write_audit
from app.services.contacts.detection_service import resolve_suggestion
from app.services.contacts.errors import (
    ContactNotFoundError,
    ContactWorkspaceMismatchError,
    DocumentWorkspaceMismatchError,
    InvalidContactDataError,
)


def link_document_to_contact(
    db: Session,
    *,
    document: Invoice,
    contact: Contact,
    role: str,
    organization_id: int,
    user_id: int | None = None,
    suggestion: ContactSuggestion | None = None,
    audit: bool = True,
) -> Invoice:
    if document.organization_id != organization_id:
        raise DocumentWorkspaceMismatchError()
    if contact.organization_id != organization_id:
        raise ContactWorkspaceMismatchError()

    role_clean = (role or "").strip().lower()
    if role_clean not in {"supplier", "customer"}:
        raise InvalidContactDataError("Rôle invalide (supplier ou customer)")

    if role_clean == "supplier":
        document.supplier_contact_id = contact.id
        if not document.supplier and contact.company_name:
            document.supplier = contact.company_name
    else:
        document.customer_contact_id = contact.id

    # Enrichir le type de contact si besoin (client + fournisseur)
    if role_clean == "supplier" and contact.contact_type == "customer":
        contact.contact_type = "customer_and_supplier"
    elif role_clean == "customer" and contact.contact_type == "supplier":
        contact.contact_type = "customer_and_supplier"
    elif role_clean == "customer" and contact.contact_type == "prospect":
        contact.contact_type = "customer"

    db.add(document)
    db.add(contact)
    db.commit()
    db.refresh(document)

    if suggestion:
        resolve_suggestion(db, suggestion=suggestion, status="linked", user_id=user_id)

    if audit:
        write_audit(
            db,
            user_id=user_id,
            organization_id=organization_id,
            action=f"document_linked_to_contact:{document.id}:{contact.id}:{role_clean}",
            module="contacts",
        )
    return document


def get_org_contact(db: Session, contact_id: int, organization_id: int) -> Contact:
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.organization_id == organization_id)
        .first()
    )
    if not contact:
        raise ContactNotFoundError()
    return contact
