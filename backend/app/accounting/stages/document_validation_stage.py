"""Stage validation documentaire — réutilise validate_financials."""

from __future__ import annotations

from typing import Any

from app.agents.validator import validate_financials
from app.schemas import ExtractionResult


def run_document_validation(
    extraction: ExtractionResult,
    *,
    confidence_threshold: float = 0.85,
) -> dict[str, Any]:
    """Sortie normalisée ; logique métier déléguée à validate_financials."""
    result = validate_financials(
        extraction,
        confidence_threshold=confidence_threshold,
    )
    errors = list(result.anomalies)
    # Les champs manquants sont des erreurs documentaires
    missing = list(result.missing_fields)
    if not result.is_valid and missing:
        status = "invalid"
    elif missing or result.needs_review:
        status = "warning" if result.is_valid or missing else "invalid"
        if missing and not result.is_valid:
            status = "invalid"
    else:
        status = "valid"

    if missing and status == "valid":
        status = "warning"

    return {
        "status": status,
        "errors": errors,
        "warnings": [f"Champ manquant: {m}" for m in missing] if status != "invalid" else [],
        "missing_fields": missing,
        "requires_review": bool(result.needs_review),
        "is_valid": bool(result.is_valid),
    }
