"""Sanitisation — pas de montants / noms / payloads."""

from __future__ import annotations

from typing import Any


_ALLOWED_PARAM_KEYS = frozenset(
    {
        "difference_category",
        "reason_code",
        "status",
        "retryable",
        "bridge_key",
        "product_key",
        "attempt_number",
        "schema_key",
        "schema_version",
    }
)


def sanitize_metadata(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    out: dict[str, Any] = {}
    for k, v in data.items():
        if k not in _ALLOWED_PARAM_KEYS:
            continue
        if isinstance(v, (str, int, bool, float)) and not isinstance(v, bool):
            if isinstance(v, str) and len(v) > 64:
                out[k] = v[:64]
            else:
                out[k] = v
        elif isinstance(v, bool):
            out[k] = v
    return out


def sanitize_error_message(msg: str | None, *, max_len: int = 255) -> str | None:
    if not msg:
        return None
    s = str(msg).strip().replace("\n", " ")
    return s[:max_len] if s else None
