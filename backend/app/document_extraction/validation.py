"""Validation stricte des sorties IA — aucune sortie invalide ne devient officielle."""

from __future__ import annotations

import json
import math
import re
from typing import Any

MAX_JSON_DEPTH = 8
MAX_JSON_SIZE = 200_000
MAX_ARRAY_LEN = 500
MAX_KEYS = 200

_ALLOWED_TOP_KEYS = frozenset(
    {
        "document_number",
        "quote_number",
        "credit_note_number",
        "receipt_number",
        "document_date",
        "issue_date",
        "credit_note_date",
        "due_date",
        "validity_date",
        "currency",
        "document_language",
        "supplier",
        "customer",
        "merchant_name",
        "merchant_address",
        "amounts",
        "taxes",
        "payment",
        "line_items",
        "transactions",
        "metadata",
        "notes",
        "reason",
        "original_invoice_number",
        "bank_name",
        "account_holder",
        "iban_masked",
        "bic",
        "statement_period_start",
        "statement_period_end",
        "opening_balance",
        "closing_balance",
        "contract_title",
        "contract_type",
        "contract_number",
        "parties",
        "effective_date",
        "end_date",
        "renewal_type",
        "termination_notice",
        "total_value",
        "payment_terms",
        "governing_law",
        "jurisdiction",
        "signatories",
        "key_clauses",
        "warnings",
        "title",
        "summary",
        "references",
        "invoice",  # legacy AI shape
        "confidence",
    }
)


def parse_strict_json(raw: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse JSON strict. Refuse markdown/text libre. Retourne (obj|None, errors)."""
    errors: list[str] = []
    if raw is None:
        return None, ["empty_output"]
    if isinstance(raw, dict):
        obj = raw
    elif isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8", errors="ignore")
        except Exception:
            return None, ["undecodable_bytes"]
        return parse_strict_json(raw)
    elif isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None, ["empty_output"]
        # Strip optional markdown fence once
        if s.startswith("```"):
            s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
            s = re.sub(r"\s*```$", "", s)
            s = s.strip()
            errors.append("markdown_fence_stripped")
        if not (s.startswith("{") or s.startswith("[")):
            return None, ["not_json_object"]
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            # réparation limitée : tronquer après dernière }
            repaired = _limited_repair(s)
            if repaired is None:
                return None, ["json_parse_failed"]
            parsed = repaired
            errors.append("json_repaired_limited")
        if not isinstance(parsed, dict):
            return None, ["json_not_object"]
        obj = parsed
    else:
        return None, ["unsupported_type"]

    ok, verrs = validate_structured_object(obj)
    errors.extend(verrs)
    if not ok:
        return None, errors
    return obj, errors


def validate_structured_object(obj: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        blob = json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return False, ["json_serialize_failed"]
    if len(blob) > MAX_JSON_SIZE:
        return False, ["json_too_large"]
    depth = _depth(obj)
    if depth > MAX_JSON_DEPTH:
        return False, ["json_too_deep"]
    if len(obj) > MAX_KEYS:
        return False, ["too_many_keys"]
    unknown = [k for k in obj.keys() if k not in _ALLOWED_TOP_KEYS]
    if unknown:
        # strip unknown — ne pas accepter tels quels
        for k in unknown:
            obj.pop(k, None)
        errors.append("unknown_keys_stripped")
    if not _sanitize_values(obj, errors):
        return False, errors
    if any(e.startswith("invalid_value") for e in errors):
        return False, errors
    return True, errors


def _limited_repair(s: str) -> dict[str, Any] | None:
    """Une seule tentative : couper jusqu'à la dernière accolade fermante."""
    idx = s.rfind("}")
    if idx <= 0:
        return None
    try:
        parsed = json.loads(s[: idx + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _depth(v: Any, d: int = 0) -> int:
    if isinstance(v, dict):
        if not v:
            return d + 1
        return max(_depth(x, d + 1) for x in v.values())
    if isinstance(v, list):
        if not v:
            return d + 1
        return max(_depth(x, d + 1) for x in v[:MAX_ARRAY_LEN])
    return d


def _sanitize_values(obj: Any, errors: list[str], *, path: str = "") -> bool:
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if not _sanitize_values(v, errors, path=f"{path}.{k}" if path else k):
                obj[k] = None
                errors.append(f"invalid_value:{path}.{k}" if path else f"invalid_value:{k}")
        return True
    if isinstance(obj, list):
        if len(obj) > MAX_ARRAY_LEN:
            del obj[MAX_ARRAY_LEN:]
            errors.append("array_truncated")
        for i, v in enumerate(list(obj)):
            if not _sanitize_values(v, errors, path=f"{path}[{i}]"):
                obj[i] = None
        return True
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return False
        return True
    if isinstance(obj, (str, int, bool)) or obj is None:
        return True
    # refuse arbitrary objects
    return False
