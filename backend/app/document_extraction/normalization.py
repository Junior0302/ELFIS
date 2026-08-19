"""Normalisation des champs extraits."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

_DATE_FR = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
_DATE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _norm_amount(raw: Any) -> tuple[Any, str, list[str]]:
    warnings: list[str] = []
    if raw is None:
        return None, "missing", warnings
    if isinstance(raw, (int, float, Decimal)):
        return Decimal(str(raw)), "normalized", warnings
    s = str(raw).strip().replace("€", "").replace(" ", "").replace("\u00a0", "")
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    if s.startswith("-"):
        neg = True
        s = s[1:]
    # European: 1.234,56 vs 1234.56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        val = Decimal(s)
        if neg:
            val = -val
        return val, "normalized", warnings
    except (InvalidOperation, ValueError):
        warnings.append("amount_unparseable")
        return str(raw), "raw_only", warnings


def _norm_date(raw: Any) -> tuple[Any, str, list[str]]:
    warnings: list[str] = []
    if raw is None:
        return None, "missing", warnings
    s = str(raw).strip()
    m = _DATE_ISO.match(s)
    if m:
        return s, "normalized", warnings
    m = _DATE_FR.match(s)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2:
            y = "20" + y
        # Ambiguïté US/FR si day>12 impossible sinon warning
        day, month = int(d), int(mo)
        if day > 12:
            return f"{y}-{month:02d}-{day:02d}", "normalized", warnings
        if month > 12:
            return f"{y}-{day:02d}-{month:02d}", "normalized", warnings
        warnings.append("date_ambiguous_dmy")
        return f"{y}-{month:02d}-{day:02d}", "normalized_assumed_dmy", warnings
    warnings.append("date_unparseable")
    return s, "raw_only", warnings


def _mask_iban(iban: str) -> str:
    iban = re.sub(r"\s+", "", iban.upper())
    if len(iban) < 8:
        return "****"
    return iban[:4] + "****" + iban[-4:]


def normalize_extraction(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retourne (normalized_data, field_normalization_meta)."""
    out = dict(data)
    meta: dict[str, Any] = {}

    for date_key in ("document_date", "due_date", "issue_date", "validity_date", "credit_note_date"):
        if date_key in out:
            val, status, warns = _norm_date(out[date_key])
            meta[date_key] = {
                "raw_value": data.get(date_key),
                "normalized_value": val,
                "normalization_status": status,
                "warnings": warns,
            }
            out[date_key] = val

    amounts = out.get("amounts")
    if isinstance(amounts, dict):
        new_amounts = {}
        for k, v in amounts.items():
            val, status, warns = _norm_amount(v)
            path = f"amounts.{k}"
            meta[path] = {
                "raw_value": v,
                "normalized_value": str(val) if isinstance(val, Decimal) else val,
                "normalization_status": status,
                "warnings": warns,
            }
            new_amounts[k] = float(val) if isinstance(val, Decimal) else val
        out["amounts"] = new_amounts

    for money_key in ("total_including_tax", "subtotal_excluding_tax", "total_tax"):
        if money_key in out:
            val, status, warns = _norm_amount(out[money_key])
            meta[money_key] = {
                "raw_value": data.get(money_key),
                "normalized_value": str(val) if isinstance(val, Decimal) else val,
                "normalization_status": status,
                "warnings": warns,
            }
            out[money_key] = float(val) if isinstance(val, Decimal) else val

    if out.get("currency"):
        cur = str(out["currency"]).upper().strip()
        if len(cur) == 3:
            out["currency"] = cur
            meta["currency"] = {
                "raw_value": data.get("currency"),
                "normalized_value": cur,
                "normalization_status": "normalized",
                "warnings": [],
            }
        else:
            meta["currency"] = {
                "raw_value": data.get("currency"),
                "normalized_value": cur,
                "normalization_status": "raw_only",
                "warnings": ["currency_unknown"],
            }

    supplier = out.get("supplier")
    if isinstance(supplier, dict) and supplier.get("iban"):
        raw = str(supplier["iban"])
        supplier = dict(supplier)
        supplier["iban_masked"] = _mask_iban(raw)
        # conserver iban pour validation interne — sera filtré API si pas view_sensitive
        out["supplier"] = supplier
        meta["supplier.iban"] = {
            "raw_value": "[REDACTED]",
            "normalized_value": supplier["iban_masked"],
            "normalization_status": "masked",
            "warnings": [],
        }

    return out, meta
