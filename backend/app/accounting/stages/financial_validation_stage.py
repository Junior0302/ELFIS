"""Stage validation financière — Decimal + réutilisation validate_financials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.accounting.accounting_security import amount_tolerance, to_decimal
from app.agents.validator import validate_financials
from app.config import settings
from app.schemas import ExtractionResult


def run_financial_validation(extraction: ExtractionResult) -> dict[str, Any]:
    """
    Contrôle HT + TVA = TTC en Decimal avec tolérance configurable,
    puis enrichit avec validate_financials (taux TVA, anomalies).
    """
    legacy = validate_financials(
        extraction,
        confidence_threshold=float(settings.elfis_accounting_auto_ready_confidence),
        default_vat_rate=20.0,
    )

    ht = to_decimal(extraction.amount_ht, field="amount_ht") if extraction.amount_ht is not None else None
    tva = to_decimal(extraction.amount_tva, field="amount_tva") if extraction.amount_tva is not None else None
    ttc = to_decimal(extraction.amount_ttc, field="amount_ttc") if extraction.amount_ttc is not None else None

    errors: list[str] = []
    warnings: list[str] = []
    balanced_amounts = True
    expected_ttc: float | None = None
    actual_ttc: float | None = float(ttc) if ttc is not None else None
    difference = 0.0

    if ht is not None and tva is not None and ttc is not None:
        expected = (ht + tva).quantize(Decimal("0.01"))
        expected_ttc = float(expected)
        diff = abs(expected - ttc)
        difference = float(diff)
        tol = amount_tolerance()
        if diff > tol:
            balanced_amounts = False
            errors.append(
                f"Incohérence HT + TVA ≠ TTC (attendu {expected}, relevé {ttc}, Δ={diff})"
            )
        elif diff > Decimal("0"):
            warnings.append(f"Écart d'arrondi TTC dans la tolérance ({diff})")

    # Negatives: allowed for credit notes only
    doc = (extraction.document_type or "").lower()
    is_credit = doc in ("avoir", "credit_note")
    for label, val in (("HT", ht), ("TVA", tva), ("TTC", ttc)):
        if val is not None and val < 0 and not is_credit:
            errors.append(f"Montant {label} négatif non autorisé pour ce type")

    if ttc is not None and ttc == 0:
        warnings.append("Montant TTC nul")

    # Merge legacy anomalies not already covered
    for a in legacy.anomalies:
        if "HT + TVA" in a:
            continue  # remplacé par Decimal
        if a not in errors and a not in warnings:
            if "confiance" in a.lower():
                warnings.append(a)
            else:
                errors.append(a)

    if errors:
        status = "invalid"
    elif warnings or legacy.needs_review:
        status = "warning"
    else:
        status = "valid"

    return {
        "status": status,
        "balanced_amounts": balanced_amounts,
        "expected_ttc": expected_ttc,
        "actual_ttc": actual_ttc,
        "difference": difference,
        "errors": errors,
        "warnings": warnings,
        "requires_review": bool(errors or warnings or legacy.needs_review),
    }
