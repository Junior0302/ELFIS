from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Invoice
from app.models_saas import Contact, ContactSuggestion
from app.services.auth import write_audit
from app.services.contacts.detection_service import resolve_suggestion
from app.services.contacts.duplicate_service import find_duplicates
from app.services.contacts.errors import DuplicateContactError, InvalidContactDataError
from app.services.contacts.linking_service import link_document_to_contact
from app.services.contacts.validators import require_minimal_identity, validate_optional_identifiers


def serialize_contact(contact: Contact) -> dict:
    return {
        "id": contact.id,
        "organization_id": contact.organization_id,
        "contact_type": contact.contact_type,
        "status": contact.status,
        "company_name": contact.company_name,
        "trade_name": contact.trade_name,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "siren": contact.siren,
        "siret": contact.siret,
        "vat_number": contact.vat_number,
        "email": contact.email,
        "phone": contact.phone,
        "address_line_1": contact.address_line_1,
        "address_line_2": contact.address_line_2,
        "postal_code": contact.postal_code,
        "city": contact.city,
        "country": contact.country,
        "iban": contact.iban,
        "bic": contact.bic,
        "payment_terms": contact.payment_terms,
        "payment_method": contact.payment_method,
        "source": contact.source,
        "source_document_id": contact.source_document_id,
        "extraction_confidence": contact.extraction_confidence,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


def create_contact_from_document(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    document: Invoice,
    role: str,
    contact_type: str,
    confirmed_data: dict,
    suggestion: ContactSuggestion | None = None,
    confidence: float | None = None,
) -> Contact:
    if document.organization_id != organization_id:
        raise InvalidContactDataError("Document hors espace")

    data = validate_optional_identifiers(confirmed_data)
    require_minimal_identity(data)
    ctype = (contact_type or role or "supplier").strip()
    if ctype not in {"customer", "supplier", "prospect", "customer_and_supplier"}:
        raise InvalidContactDataError("Type de contact invalide")

    duplicates = find_duplicates(db, organization_id=organization_id, extracted=data)
    hard = [d for d in duplicates if d["match_score"] >= 95 and d["match_type"] in {"siret", "vat_number", "siren"}]
    if hard:
        raise DuplicateContactError(
            f"Contact déjà existant : {hard[0]['company_name']} (id {hard[0]['contact_id']})"
        )

    contact = Contact(
        organization_id=organization_id,
        user_id=user_id,
        contact_type=ctype,
        status="active",
        company_name=data.get("company_name") or "",
        trade_name=data.get("trade_name") or "",
        first_name=data.get("first_name") or "",
        last_name=data.get("last_name") or "",
        siren=data.get("siren") or "",
        siret=data.get("siret") or "",
        vat_number=data.get("vat_number") or "",
        email=data.get("email") or "",
        phone=data.get("phone") or "",
        address_line_1=data.get("address_line_1") or "",
        address_line_2=data.get("address_line_2") or "",
        postal_code=data.get("postal_code") or "",
        city=data.get("city") or "",
        country=data.get("country") or "France",
        iban=data.get("iban") or "",
        bic=data.get("bic") or "",
        payment_terms=data.get("payment_terms") or "",
        payment_method=data.get("payment_method") or "",
        source="document_extraction",
        source_document_id=document.id,
        extraction_confidence=confidence,
        created_by=user_id,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    link_document_to_contact(
        db,
        document=document,
        contact=contact,
        role=role,
        organization_id=organization_id,
        user_id=user_id,
        audit=False,
    )
    if suggestion:
        resolve_suggestion(db, suggestion=suggestion, status="accepted", user_id=user_id)

    write_audit(
        db,
        user_id=user_id,
        organization_id=organization_id,
        action=f"contact_created_from_document:{contact.id}:doc:{document.id}",
        module="contacts",
    )
    return contact


def update_contact(
    db: Session,
    *,
    contact: Contact,
    payload: dict,
    user_id: int | None,
    allow_iban_replace: bool = False,
) -> Contact:
    data = validate_optional_identifiers({**serialize_contact(contact), **payload})
    require_minimal_identity(data)

    new_iban = data.get("iban") or ""
    if contact.iban and new_iban and contact.iban != new_iban and not allow_iban_replace:
        from app.services.contacts.errors import UnsafeBankDetailUpdateError

        raise UnsafeBankDetailUpdateError()

    for key in (
        "contact_type",
        "status",
        "company_name",
        "trade_name",
        "first_name",
        "last_name",
        "siren",
        "siret",
        "vat_number",
        "email",
        "phone",
        "address_line_1",
        "address_line_2",
        "postal_code",
        "city",
        "country",
        "iban",
        "bic",
        "payment_terms",
        "payment_method",
    ):
        if key in payload or key in data:
            setattr(contact, key, data.get(key, getattr(contact, key)))

    db.add(contact)
    db.commit()
    db.refresh(contact)
    write_audit(
        db,
        user_id=user_id,
        organization_id=contact.organization_id,
        action=f"contact_updated:{contact.id}",
        module="contacts",
    )
    return contact
