"""Non-destructive duplicate detection for SharedRelation projections."""

from __future__ import annotations

import re

from app.services.shared_relations.contract import PossibleDuplicate, SharedRelation


def _norm_email(value: str) -> str:
    return (value or "").strip().lower()


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value or "")
    if digits.startswith("33") and len(digits) > 9:
        digits = "0" + digits[2:]
    return digits


def _norm_tax(value: str) -> str:
    return re.sub(r"[\s.]", "", (value or "").upper())


def _norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _email_domain(email: str) -> str:
    e = _norm_email(email)
    if "@" not in e:
        return ""
    return e.split("@", 1)[1]


def score_pair(left: SharedRelation, right: SharedRelation) -> PossibleDuplicate | None:
    if left.id == right.id:
        return None
    if left.organization_id != right.organization_id:
        return None

    fields: list[str] = []
    score = 0.0

    l_siren = _norm_tax(left.siren)
    r_siren = _norm_tax(right.siren)
    if l_siren and r_siren and l_siren == r_siren:
        fields.append("siren")
        score += 0.45

    l_siret = _norm_tax(left.siret)
    r_siret = _norm_tax(right.siret)
    if l_siret and r_siret and l_siret == r_siret:
        fields.append("siret")
        score += 0.5

    l_tax = _norm_tax(left.tax_number)
    r_tax = _norm_tax(right.tax_number)
    if l_tax and r_tax and l_tax == r_tax:
        fields.append("tax_number")
        score += 0.35

    l_emails = {_norm_email(e) for e in left.emails if e}
    r_emails = {_norm_email(e) for e in right.emails if e}
    if l_emails & r_emails:
        fields.append("email")
        score += 0.4

    l_phones = {_norm_phone(p) for p in left.phones if _norm_phone(p)}
    r_phones = {_norm_phone(p) for p in right.phones if _norm_phone(p)}
    if l_phones & r_phones:
        fields.append("phone")
        score += 0.25

    l_name = _norm_name(left.legal_name or left.display_name)
    r_name = _norm_name(right.legal_name or right.display_name)
    if l_name and r_name and l_name == r_name:
        fields.append("legal_name")
        score += 0.2
        # boost if address city also matches
        l_cities = {(a.city or "").strip().lower() for a in left.addresses if a.city}
        r_cities = {(a.city or "").strip().lower() for a in right.addresses if a.city}
        if l_cities & r_cities:
            fields.append("city")
            score += 0.15

    l_domains = {_email_domain(e) for e in left.emails if _email_domain(e)}
    r_domains = {_email_domain(e) for e in right.emails if _email_domain(e)}
    public = {"gmail.com", "yahoo.fr", "yahoo.com", "hotmail.com", "outlook.com", "orange.fr", "free.fr"}
    shared_domains = (l_domains & r_domains) - public
    if shared_domains and "email" not in fields:
        fields.append("email_domain")
        score += 0.15

    if not fields or score < 0.35:
        return None

    return PossibleDuplicate(
        confidence=min(1.0, round(score, 3)),
        matching_fields=fields,
        related_entity_ids=[left.id, right.id],
        left_id=left.id,
        right_id=right.id,
    )


def find_duplicates(relations: list[SharedRelation]) -> list[PossibleDuplicate]:
    """Pairwise scan — no auto-merge. O(n²) acceptable for org-scoped V1 lists."""
    out: list[PossibleDuplicate] = []
    seen_pairs: set[tuple[str, str]] = set()
    for i, left in enumerate(relations):
        for right in relations[i + 1 :]:
            pair = score_pair(left, right)
            if not pair:
                continue
            key = tuple(sorted([pair.left_id, pair.right_id]))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            out.append(pair)
    out.sort(key=lambda d: d.confidence, reverse=True)
    return out
