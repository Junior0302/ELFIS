"""Stage revue — score requires_review."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.config import settings


def determine_review_status(
    *,
    confidence: float | None,
    document_validation: dict[str, Any],
    financial_validation: dict[str, Any],
    mapping: dict[str, Any],
    amount_ttc: Decimal | float | None,
    document_type_supported: bool,
    manual_edit: bool = False,
) -> tuple[bool, list[str], float | None]:
    reasons: list[str] = []
    conf = float(confidence) if confidence is not None else None
    auto_ready = float(settings.elfis_accounting_auto_ready_confidence)
    high_amount = Decimal(str(settings.elfis_accounting_high_amount_review_threshold))

    if not document_type_supported:
        reasons.append("document_type_unsupported")

    if document_validation.get("status") in ("invalid", "warning"):
        reasons.append("document_validation_issue")
    if document_validation.get("missing_fields"):
        reasons.append("incomplete_document")

    if financial_validation.get("status") == "invalid":
        reasons.append("financial_error")
    elif financial_validation.get("status") == "warning":
        reasons.append("financial_warning")

    if mapping.get("status") in ("unbalanced", "empty", "skipped"):
        reasons.append("mapping_issue")
    if mapping.get("used_default_accounts") and settings.elfis_accounting_require_review_on_default_account:
        reasons.append("default_account_used")

    if conf is not None and conf < auto_ready:
        reasons.append("low_confidence")

    if amount_ttc is not None and Decimal(str(amount_ttc)) >= high_amount:
        reasons.append("high_amount")

    if manual_edit:
        reasons.append("manual_modification")

    requires_review = bool(reasons)
    # Même sans raisons, V1 n'auto-valide jamais — ready_for_validation seulement
    return requires_review, reasons, conf
