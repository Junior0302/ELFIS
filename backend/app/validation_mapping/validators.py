"""Contrôles de format — Validation Center (aucune correction silencieuse)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.config import settings
from app.document_extraction import AMOUNT_TOLERANCE

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SIREN = re.compile(r"^\d{9}$")
_SIRET = re.compile(r"^\d{14}$")
_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def validate_document_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    if not data.get("document_number") and not data.get("quote_number") and not data.get(
        "credit_note_number"
    ):
        warnings.append("DOCUMENT_NUMBER_MISSING")

    for dk in ("document_date", "issue_date", "credit_note_date", "due_date"):
        val = data.get(dk)
        if val and not _DATE.match(str(val)):
            errors.append(f"INVALID_DATE:{dk}")

    cur = data.get("currency")
    if cur and not _CURRENCY.match(str(cur).upper()):
        warnings.append("CURRENCY_FORMAT")

    amounts = data.get("amounts") if isinstance(data.get("amounts"), dict) else {}
    tol = Decimal(str(getattr(settings, "document_validation_amount_tolerance", None) or AMOUNT_TOLERANCE))
    sub = _dec(amounts.get("subtotal_excluding_tax"))
    tax = _dec(amounts.get("total_tax"))
    total = _dec(amounts.get("total_including_tax"))
    if sub is not None and tax is not None and total is not None:
        if abs((sub + tax) - total) > tol:
            errors.append("AMOUNT_MISMATCH")
        else:
            infos.append("amounts_ok")

    supplier = data.get("supplier") if isinstance(data.get("supplier"), dict) else {}
    for key, rx, code in (
        ("registration_number", _SIREN, "SIREN_INVALID"),
        ("vat_number", re.compile(r"^[A-Z]{2}[A-Z0-9]{8,12}$"), "VAT_INVALID"),
        ("iban", _IBAN, "IBAN_INVALID"),
        ("email", _EMAIL, "EMAIL_INVALID"),
    ):
        v = supplier.get(key)
        if v:
            raw = re.sub(r"\s+", "", str(v).upper()) if key != "email" else str(v).strip()
            if key == "registration_number":
                digits = re.sub(r"\D", "", str(v))
                if len(digits) == 14:
                    if not _SIRET.match(digits):
                        warnings.append("SIRET_INVALID")
                elif len(digits) == 9:
                    if not _SIREN.match(digits):
                        warnings.append(code)
                else:
                    warnings.append(code)
            elif key == "email":
                if not _EMAIL.match(raw):
                    warnings.append(code)
            else:
                if not rx.match(raw):
                    warnings.append(code)

    phone = supplier.get("phone")
    if phone and len(re.sub(r"\D", "", str(phone))) < 8:
        warnings.append("PHONE_SUSPECT")

    return {
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "ok": not errors,
    }
