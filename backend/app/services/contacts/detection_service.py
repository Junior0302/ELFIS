from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import CompanySettings, Invoice
from app.models_saas import Contact, ContactSuggestion, Organization
from app.services.contacts.duplicate_service import find_duplicates, suggested_action_from_matches
from app.services.contacts.normalize import (
    digits_only,
    normalize_company_name,
    normalize_vat,
)

logger = logging.getLogger(__name__)


def _parse_address(address: str | None) -> dict:
    text = (address or "").strip()
    if not text:
        return {"address_line_1": "", "postal_code": "", "city": ""}
    # Heuristique FR : «... 67000 Strasbourg»
    import re

    match = re.search(r"(\d{5})\s+([A-Za-zÀ-ÿ' \-]+)\s*$", text)
    if match:
        postal = match.group(1)
        city = match.group(2).strip()
        line1 = text[: match.start()].strip(" ,")
        return {"address_line_1": line1 or text, "postal_code": postal, "city": city}
    return {"address_line_1": text, "postal_code": "", "city": ""}


def _extraction_dict(invoice: Invoice) -> dict:
    if not invoice.raw_extraction:
        return {
            "supplier": invoice.supplier,
            "document_type": invoice.document_type or "facture",
        }
    try:
        data = json.loads(invoice.raw_extraction)
        if isinstance(data, dict):
            data.setdefault("supplier", invoice.supplier)
            data.setdefault("document_type", invoice.document_type or "facture")
            return data
    except Exception:
        pass
    return {"supplier": invoice.supplier, "document_type": invoice.document_type or "facture"}


def _own_company_keys(org: Organization | None, settings: CompanySettings | None) -> dict:
    siret = digits_only((settings.siret if settings else "") or "")
    siren = digits_only((org.siren if org else "") or "") or (siret[:9] if len(siret) == 14 else "")
    vat = normalize_vat((settings.vat_number if settings else "") or (org.vat_number if org else ""))
    names = {
        normalize_company_name(org.name if org else ""),
        normalize_company_name(org.legal_name if org else ""),
        normalize_company_name(settings.company_name if settings else ""),
    }
    names.discard("")
    return {"siret": siret, "siren": siren, "vat": vat, "names": names}


def _is_own_company(extracted: dict, own: dict) -> bool:
    siret = digits_only(extracted.get("siret"))
    siren = digits_only(extracted.get("siren")) or (siret[:9] if len(siret) == 14 else "")
    vat = normalize_vat(extracted.get("vat_number"))
    name = normalize_company_name(extracted.get("company_name") or "")
    if own["siret"] and siret and siret == own["siret"]:
        return True
    if own["siren"] and siren and siren == own["siren"]:
        return True
    if own["vat"] and vat and vat == own["vat"]:
        return True
    if name and name in own["names"]:
        return True
    return False


def _detect_roles(document_type: str, direction_hint: str | None = None) -> list[tuple[str, str]]:
    """
    Retourne [(role, suggested_contact_type), ...].
    Pour les dépôts ComptaPilot (factures reçues), l’émetteur = fournisseur par défaut.
    """
    dtype = (document_type or "facture").lower().strip()
    hint = (direction_hint or "").lower().strip()

    if "devis" in dtype:
        if hint in {"sent", "emis", "envoyé", "envoye"}:
            return [("customer", "prospect")]
        # Devis reçu (fournisseur potentiel) — défaut dépôt
        return [("supplier", "supplier")]

    if "avoir" in dtype or "credit" in dtype:
        if hint in {"client", "vente", "sales"}:
            return [("customer", "customer")]
        return [("supplier", "supplier")]

    if hint in {"vente", "sales", "client", "emis", "envoyé", "envoye"}:
        return [("customer", "customer")]

    # Facture fournisseur reçue (cas principal du dépôt)
    return [("supplier", "supplier")]


def _party_from_extraction(raw: dict, role: str) -> dict:
    addr = _parse_address(
        raw.get("supplier_address") if role == "supplier" else raw.get("customer_address")
    )
    if role == "supplier":
        company = (raw.get("supplier") or "").strip()
        return {
            "company_name": company,
            "siret": raw.get("supplier_siret") or "",
            "siren": raw.get("supplier_siren") or "",
            "vat_number": raw.get("supplier_vat") or "",
            "email": raw.get("supplier_email") or "",
            "phone": raw.get("supplier_phone") or "",
            "iban": raw.get("supplier_iban") or "",
            "bic": raw.get("supplier_bic") or "",
            "payment_terms": raw.get("payment_terms") or "",
            "payment_method": raw.get("payment_method") or "",
            **addr,
        }
    company = (raw.get("customer_name") or "").strip()
    return {
        "company_name": company,
        "siret": raw.get("customer_siret") or "",
        "siren": "",
        "vat_number": raw.get("customer_vat") or "",
        "email": raw.get("customer_email") or "",
        "phone": "",
        "iban": "",
        "bic": "",
        "payment_terms": raw.get("payment_terms") or "",
        "payment_method": raw.get("payment_method") or "",
        **addr,
    }


def _enrichment_fields(contact: Contact, extracted: dict) -> dict:
    """Champs nouveaux détectés (jamais IBAN silencieux)."""
    mapping = {
        "email": extracted.get("email") or "",
        "phone": extracted.get("phone") or "",
        "address_line_1": extracted.get("address_line_1") or "",
        "postal_code": extracted.get("postal_code") or "",
        "city": extracted.get("city") or "",
        "vat_number": extracted.get("vat_number") or "",
        "siret": extracted.get("siret") or "",
        "siren": extracted.get("siren") or "",
        "bic": extracted.get("bic") or "",
        "payment_terms": extracted.get("payment_terms") or "",
        "payment_method": extracted.get("payment_method") or "",
    }
    new_fields: dict = {}
    for key, value in mapping.items():
        value = (value or "").strip()
        if not value:
            continue
        current = (getattr(contact, key, "") or "").strip()
        if not current:
            new_fields[key] = value

    new_iban = (extracted.get("iban") or "").strip()
    if new_iban:
        current_iban = (contact.iban or "").strip()
        if not current_iban:
            new_fields["iban"] = new_iban
        elif digits_only(current_iban) != digits_only(new_iban):
            new_fields["iban_conflict"] = new_iban
    return new_fields


def _confidence_for(extracted: dict, action: str, matches: list[dict]) -> float:
    score = 55.0
    if extracted.get("company_name"):
        score += 15
    if digits_only(extracted.get("siret")):
        score += 20
    if normalize_vat(extracted.get("vat_number")):
        score += 5
    if extracted.get("city") or extracted.get("postal_code"):
        score += 5
    if matches:
        score = max(score, float(matches[0]["match_score"]))
    if action == "create_contact" and not digits_only(extracted.get("siret")):
        score = min(score, 80)
    return round(min(score, 99.0), 1)


def serialize_suggestion(row: ContactSuggestion) -> dict:
    try:
        extracted = json.loads(row.extracted_data_json or "{}")
    except Exception:
        extracted = {}
    try:
        duplicates = json.loads(row.duplicates_json or "[]")
    except Exception:
        duplicates = []
    try:
        new_fields = json.loads(row.new_fields_json or "{}")
    except Exception:
        new_fields = {}
    return {
        "id": row.id,
        "document_id": row.document_id,
        "role": row.role,
        "status": row.status,
        "suggested_contact_type": row.suggested_contact_type,
        "suggested_action": row.suggested_action,
        "confidence": row.confidence,
        "requires_user_confirmation": True,
        "extracted_data": extracted,
        "possible_duplicates": duplicates,
        "matched_contact_id": row.matched_contact_id,
        "new_fields": new_fields,
        "iban_alert": bool(new_fields.get("iban_conflict")),
    }


def list_pending_suggestions(db: Session, *, document_id: int, organization_id: int) -> list[dict]:
    rows = (
        db.query(ContactSuggestion)
        .filter(
            ContactSuggestion.document_id == document_id,
            ContactSuggestion.organization_id == organization_id,
            ContactSuggestion.status == "pending",
        )
        .order_by(ContactSuggestion.id.asc())
        .all()
    )
    return [serialize_suggestion(r) for r in rows]


def generate_suggestions(
    db: Session,
    *,
    invoice: Invoice,
    organization_id: int | None = None,
    persist: bool = True,
) -> list[dict]:
    """Génère (et optionnellement persiste) les suggestions pour un document."""
    org_id = organization_id or invoice.organization_id
    raw = _extraction_dict(invoice)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    settings = (
        db.query(CompanySettings).filter(CompanySettings.organization_id == org_id).first()
    )
    own = _own_company_keys(org, settings)
    roles = _detect_roles(
        str(raw.get("document_type") or invoice.document_type or "facture"),
        direction_hint=str(
            raw.get("direction")
            or raw.get("document_direction")
            or raw.get("flow")
            or ""
        ),
    )

    # Ne pas recréer des suggestions pending déjà présentes pour le même rôle
    existing_pending = {
        r.role
        for r in db.query(ContactSuggestion)
        .filter(
            ContactSuggestion.document_id == invoice.id,
            ContactSuggestion.organization_id == org_id,
            ContactSuggestion.status == "pending",
        )
        .all()
    }
    ignored_roles = {
        r.role
        for r in db.query(ContactSuggestion)
        .filter(
            ContactSuggestion.document_id == invoice.id,
            ContactSuggestion.organization_id == org_id,
            ContactSuggestion.status == "ignored",
        )
        .all()
    }

    created: list[ContactSuggestion] = []
    for role, contact_type in roles:
        if role in ignored_roles:
            continue
        if role in existing_pending:
            continue
        # Déjà lié sur le document
        if role == "supplier" and invoice.supplier_contact_id:
            continue
        if role == "customer" and invoice.customer_contact_id:
            continue

        extracted = _party_from_extraction(raw, role)
        if not (extracted.get("company_name") or "").strip():
            continue
        if _is_own_company(extracted, own):
            continue

        matches = find_duplicates(db, organization_id=org_id, extracted=extracted)
        action, matched_id = suggested_action_from_matches(matches)
        new_fields: dict = {}
        if matched_id and action in {"link_existing_contact", "review_possible_duplicate"}:
            contact = (
                db.query(Contact)
                .filter(Contact.id == matched_id, Contact.organization_id == org_id)
                .first()
            )
            if contact:
                new_fields = _enrichment_fields(contact, extracted)
                if new_fields and action == "link_existing_contact":
                    action = "enrich_existing_contact"

        confidence = _confidence_for(extracted, action, matches)
        row = ContactSuggestion(
            organization_id=org_id,
            document_id=invoice.id,
            role=role,
            status="pending",
            suggested_contact_type=contact_type,
            suggested_action=action,
            confidence=confidence,
            extracted_data_json=json.dumps(extracted, ensure_ascii=False),
            duplicates_json=json.dumps(matches[:5], ensure_ascii=False),
            matched_contact_id=matched_id,
            new_fields_json=json.dumps(new_fields, ensure_ascii=False),
        )
        if persist:
            db.add(row)
            created.append(row)
        else:
            created.append(row)

    if persist and created:
        db.commit()
        for row in created:
            db.refresh(row)

    if persist:
        return list_pending_suggestions(db, document_id=invoice.id, organization_id=org_id)

    return [
        {
            "role": r.role,
            "suggested_contact_type": r.suggested_contact_type,
            "suggested_action": r.suggested_action,
            "confidence": r.confidence,
            "requires_user_confirmation": True,
            "extracted_data": json.loads(r.extracted_data_json or "{}"),
            "possible_duplicates": json.loads(r.duplicates_json or "[]"),
            "matched_contact_id": r.matched_contact_id,
            "new_fields": json.loads(r.new_fields_json or "{}"),
        }
        for r in created
    ]


def safe_generate_suggestions(db: Session, invoice: Invoice) -> list[dict]:
    try:
        return generate_suggestions(db, invoice=invoice, persist=True)
    except Exception:
        logger.exception(
            "Unable to generate contact suggestions for document %s", invoice.id
        )
        return []


def resolve_suggestion(
    db: Session,
    *,
    suggestion: ContactSuggestion,
    status: str,
    user_id: int | None,
) -> ContactSuggestion:
    suggestion.status = status
    suggestion.resolved_at = datetime.utcnow()
    suggestion.resolved_by = user_id
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion
