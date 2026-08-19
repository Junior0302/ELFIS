"""Sanitisation extraction — jamais de valeurs métier / texte OCR."""

from __future__ import annotations

from typing import Any


def round_confidence(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, round(v, 2)))


def sanitize_warnings(items: list[str] | None, *, limit: int = 20) -> list[str] | None:
    if not items:
        return None
    out: list[str] = []
    for w in items[:limit]:
        s = str(w).replace("\n", " ")[:120]
        if s:
            out.append(s)
    return out or None


def sanitize_validation_summary(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Résumé de validation : codes et comptes uniquement, jamais de valeurs."""
    if not data:
        return None
    out: dict[str, Any] = {}
    for key in (
        "valid",
        "missing_required_fields",
        "invalid_fields",
        "warnings",
        "validation_codes",
        "requires_review",
    ):
        if key not in data:
            continue
        val = data[key]
        if key in ("missing_required_fields", "invalid_fields", "warnings", "validation_codes"):
            if isinstance(val, list):
                out[key] = [str(x)[:64] for x in val[:50]]
        elif key == "valid":
            out[key] = bool(val)
        elif key == "requires_review":
            out[key] = bool(val)
    return out or None


def mask_display_value(field_path: str, value: Any, *, sensitive: bool) -> str | None:
    if value is None:
        return None
    raw = str(value)
    if not sensitive:
        return raw[:80] if len(raw) > 80 else raw
    if len(raw) <= 4:
        return "***"
    return raw[:2] + "***" + raw[-2:]
