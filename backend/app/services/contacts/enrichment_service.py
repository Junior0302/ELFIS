from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Invoice
from app.models_saas import Contact, ContactSuggestion
from app.services.auth import write_audit
from app.services.contacts.detection_service import resolve_suggestion
from app.services.contacts.errors import (
    ContactWorkspaceMismatchError,
    DocumentWorkspaceMismatchError,
    InvalidContactDataError,
    UnsafeBankDetailUpdateError,
)
from app.services.contacts.validators import validate_optional_identifiers

_SAFE_FIELDS = {
    "email",
    "phone",
    "address_line_1",
    "address_line_2",
    "postal_code",
    "city",
    "country",
    "vat_number",
    "siret",
    "siren",
    "bic",
    "payment_terms",
    "payment_method",
    "trade_name",
}


def enrich_contact_from_document(
    db: Session,
    *,
    contact: Contact,
    document: Invoice,
    accepted_fields: list[str],
    field_values: dict | None = None,
    organization_id: int,
    user_id: int | None = None,
    suggestion: ContactSuggestion | None = None,
    confirm_iban: bool = False,
) -> Contact:
    if contact.organization_id != organization_id:
        raise ContactWorkspaceMismatchError()
    if document.organization_id != organization_id:
        raise DocumentWorkspaceMismatchError()

    values = validate_optional_identifiers(field_values or {})
    applied: list[str] = []
    iban_updated = False

    for field in accepted_fields:
        if field == "iban" or field == "iban_conflict":
            new_iban = (values.get("iban") or values.get("iban_conflict") or "").strip()
            if not new_iban:
                continue
            if contact.iban and contact.iban != new_iban and not confirm_iban:
                raise UnsafeBankDetailUpdateError(
                    "Un nouvel IBAN a été détecté. Confirmez explicitement avant de remplacer."
                )
            contact.iban = new_iban
            applied.append("iban")
            iban_updated = True
            continue
        if field not in _SAFE_FIELDS:
            raise InvalidContactDataError(f"Champ non autorisé : {field}")
        new_value = (values.get(field) or "").strip()
        if not new_value:
            continue
        current = (getattr(contact, field, "") or "").strip()
        if not current:
            setattr(contact, field, new_value)
            applied.append(field)

    if not applied:
        raise InvalidContactDataError("Aucun champ à enrichir")

    db.add(contact)
    db.commit()
    db.refresh(contact)

    if suggestion:
        resolve_suggestion(db, suggestion=suggestion, status="accepted", user_id=user_id)

    write_audit(
        db,
        user_id=user_id,
        organization_id=organization_id,
        action=f"contact_enriched_from_document:{contact.id}:doc:{document.id}:{','.join(applied)}",
        module="contacts",
    )
    if iban_updated:
        write_audit(
            db,
            user_id=user_id,
            organization_id=organization_id,
            action=f"contact_iban_updated:{contact.id}:doc:{document.id}",
            module="contacts",
        )
    return contact
