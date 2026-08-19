"""Deterministic Quote Readiness score 0–100."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.sales_proposals.enums import ReadinessLevel


def compute_readiness(
    *,
    has_company: bool,
    has_contact: bool,
    has_address: bool,
    has_legal_id: bool,
    currency: str | None,
    lines_count: int,
    lines_valid: bool,
    has_valid_until: bool,
    has_payment_terms: bool,
    has_terms: bool,
    has_owner: bool,
    has_current_version: bool,
    has_pdf: bool,
    status: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    score = 0

    def add(key: str, label: str, weight: int, ok: bool, blocker: bool = False, warn: str | None = None):
        nonlocal score
        status_val = "passed" if ok else ("failed" if blocker else "warning")
        checks.append({"key": key, "label": label, "status": status_val, "weight": weight})
        if ok:
            score += weight
        elif blocker:
            blockers.append(label)
        elif warn:
            warnings.append(warn)

    add("company", "Entreprise identifiée", 12, has_company, blocker=True)
    add("contact", "Contact principal", 8, has_contact, blocker=False, warn="Contact principal manquant")
    add("address", "Adresse entreprise", 6, has_address, warn="Adresse manquante")
    add("legal", "Identifiants légaux", 6, has_legal_id, warn="SIRET/TVA manquants")
    add("currency", "Devise", 6, bool(currency), blocker=True)
    add("lines", "Lignes présentes", 12, lines_count > 0, blocker=True)
    add("line_amounts", "Quantités et prix valides", 12, lines_valid, blocker=True)
    add("validity", "Date de validité", 8, has_valid_until, warn="Validité non renseignée")
    add("payment", "Conditions de paiement", 8, has_payment_terms, warn="Conditions de paiement non renseignées")
    add("terms", "Conditions commerciales", 6, has_terms, warn="Conditions commerciales absentes")
    add("owner", "Owner assigné", 6, has_owner, warn="Owner manquant")
    add("version", "Version active", 5, has_current_version, blocker=True)
    add("pdf", "PDF généré", 5, has_pdf, warn="PDF non généré")

    # Status coherence bonus
    if status in ("approved", "sent", "accepted") and not blockers:
        score = min(100, score + 0)

    score = max(0, min(100, score))
    if blockers:
        level = ReadinessLevel.blocked.value
    elif score >= 90:
        level = ReadinessLevel.ready.value
    elif score >= 70:
        level = ReadinessLevel.almost_ready.value
    else:
        level = ReadinessLevel.incomplete.value

    recommendations: list[str] = []
    if not has_pdf:
        recommendations.append("Générer le PDF avant envoi")
    if not has_payment_terms:
        recommendations.append("Renseigner les conditions de paiement")
    if not has_valid_until:
        recommendations.append("Définir une date de validité")

    return {
        "score": score,
        "level": level,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def lines_are_valid(lines: list[Any]) -> bool:
    if not lines:
        return False
    for line in lines:
        q = Decimal(str(getattr(line, "quantity", 0) or 0))
        p = Decimal(str(getattr(line, "unit_price", 0) or 0))
        if q <= 0:
            return False
        if p < 0:
            return False
        if not (getattr(line, "name", None) or "").strip():
            return False
    return True
