"""Sanitisation validation — jamais de montants / noms dans messages."""

from __future__ import annotations

from typing import Any


def sanitize_issue_parameters(data: dict[str, Any] | None, *, limit: int = 10) -> dict[str, Any] | None:
    if not data:
        return None
    allowed_keys = {
        "difference_category",
        "field",
        "reason",
        "expected_presence",
        "comparison",
        "tolerance_applied",
        "range",
    }
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(data.items()):
        if i >= limit:
            break
        key = str(k)[:64]
        if key not in allowed_keys:
            continue
        if isinstance(v, (str, int, bool)) or v is None:
            out[key] = str(v)[:80] if isinstance(v, str) else v
    return out or None
