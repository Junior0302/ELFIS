from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models_saas import Contact
from app.services.contacts.normalize import (
    digits_only,
    normalize_company_name,
    normalize_email,
    normalize_vat,
)


def _score_name(a: str, b: str) -> float:
    na = normalize_company_name(a)
    nb = normalize_company_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 96.0
    return round(SequenceMatcher(None, na, nb).ratio() * 100, 1)


def find_duplicates(
    db: Session,
    *,
    organization_id: int,
    extracted: dict,
    exclude_contact_id: int | None = None,
) -> list[dict]:
    """Recherche de doublons dans l’ordre SIRET → TVA → SIREN → email → nom+CP → nom+ville → fuzzy."""
    query = db.query(Contact).filter(
        Contact.organization_id == organization_id,
        Contact.status != "deleted",
    )
    if exclude_contact_id:
        query = query.filter(Contact.id != exclude_contact_id)
    contacts = query.all()
    if not contacts:
        return []

    siret = digits_only(extracted.get("siret"))
    siren = digits_only(extracted.get("siren")) or (siret[:9] if len(siret) == 14 else "")
    vat = normalize_vat(extracted.get("vat_number"))
    email = normalize_email(extracted.get("email"))
    name = extracted.get("company_name") or ""
    postal = (extracted.get("postal_code") or "").strip()
    city = (extracted.get("city") or "").strip().lower()
    norm_name = normalize_company_name(name)

    matches: list[dict] = []

    def add(contact: Contact, match_type: str, score: float) -> None:
        if any(m["contact_id"] == contact.id for m in matches):
            # garder le meilleur score
            for m in matches:
                if m["contact_id"] == contact.id and score > m["match_score"]:
                    m["match_type"] = match_type
                    m["match_score"] = score
            return
        matches.append(
            {
                "contact_id": contact.id,
                "company_name": contact.company_name,
                "contact_type": contact.contact_type,
                "siret": contact.siret,
                "match_type": match_type,
                "match_score": score,
            }
        )

    for contact in contacts:
        if siret and digits_only(contact.siret) == siret:
            add(contact, "siret", 100.0)
            continue
        if vat and normalize_vat(contact.vat_number) == vat and vat:
            add(contact, "vat_number", 98.0)
            continue
        if siren and digits_only(contact.siren) == siren and len(siren) == 9:
            add(contact, "siren", 96.0)
            continue
        if email and normalize_email(contact.email) == email and email:
            add(contact, "email", 94.0)
            continue

        c_name = normalize_company_name(contact.company_name)
        if norm_name and c_name:
            if postal and contact.postal_code.strip() == postal and c_name == norm_name:
                add(contact, "name_postal", 92.0)
                continue
            if city and contact.city.strip().lower() == city and c_name == norm_name:
                add(contact, "name_city", 88.0)
                continue
            fuzzy = _score_name(name, contact.company_name)
            if fuzzy >= 75:
                add(contact, "name_fuzzy", fuzzy)

    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches


def best_duplicate(matches: list[dict]) -> dict | None:
    return matches[0] if matches else None


def suggested_action_from_matches(matches: list[dict]) -> tuple[str, int | None]:
    """Retourne (suggested_action, matched_contact_id)."""
    top = best_duplicate(matches)
    if not top:
        return "create_contact", None
    score = float(top["match_score"])
    if score >= 95:
        return "link_existing_contact", int(top["contact_id"])
    if score >= 75:
        return "review_possible_duplicate", int(top["contact_id"])
    return "create_contact", None
