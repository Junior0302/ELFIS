"""Matching clients/fournisseurs — propositions uniquement, aucune création."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.validation_mapping.enums import MatchCategory


def _category(score: float) -> str:
    if score >= 0.95:
        return MatchCategory.EXACT.value
    if score >= 0.80:
        return MatchCategory.STRONG.value
    if score >= 0.60:
        return MatchCategory.MEDIUM.value
    if score >= 0.40:
        return MatchCategory.WEAK.value
    return MatchCategory.NO_MATCH.value


def match_party(
    db: Session,
    *,
    organization_id: int,
    party: dict[str, Any],
    party_role: str,
) -> list[dict[str, Any]]:
    """Réutilise find_duplicates contacts — ne crée jamais de fiche."""
    if not party:
        return [
            {
                "party_role": party_role,
                "category": MatchCategory.NO_MATCH.value,
                "score": 0.0,
                "contact_id": None,
                "contact_label": None,
                "matched_criteria": [],
                "explanation": "Aucune donnée partie",
            }
        ]

    extracted = {
        "company_name": party.get("name") or party.get("legal_name") or party.get("merchant_name"),
        "siret": party.get("registration_number")
        if len(str(party.get("registration_number") or "")) == 14
        else None,
        "siren": party.get("registration_number")
        if len(str(party.get("registration_number") or "")) == 9
        else None,
        "vat_number": party.get("vat_number"),
        "email": party.get("email"),
        "postal_code": party.get("postal_code"),
        "city": party.get("city"),
        "iban": party.get("iban"),
        "phone": party.get("phone"),
    }
    # SIRET/SIREN depuis registration_number
    reg = "".join(c for c in str(party.get("registration_number") or "") if c.isdigit())
    if len(reg) == 14:
        extracted["siret"] = reg
        extracted["siren"] = reg[:9]
    elif len(reg) == 9:
        extracted["siren"] = reg

    try:
        from app.services.contacts.duplicate_service import find_duplicates

        raw = find_duplicates(db, organization_id=organization_id, extracted=extracted)
    except Exception:
        raw = []

    if not raw:
        return [
            {
                "party_role": party_role,
                "category": MatchCategory.NO_MATCH.value,
                "score": 0.0,
                "contact_id": None,
                "contact_label": None,
                "matched_criteria": [],
                "explanation": "Aucun match trouvé",
            }
        ]

    out: list[dict[str, Any]] = []
    for m in raw[:5]:
        score01 = min(1.0, float(m.get("match_score") or 0) / 100.0)
        out.append(
            {
                "party_role": party_role,
                "category": _category(score01),
                "score": round(score01, 3),
                "contact_id": m.get("contact_id"),
                "contact_label": m.get("company_name"),
                "matched_criteria": [m.get("match_type")],
                "explanation": f"{m.get('match_type')} score={m.get('match_score')}",
            }
        )
    return out
