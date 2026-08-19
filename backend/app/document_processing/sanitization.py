"""Sanitisation sorties processing — jamais de contenu documentaire."""

from __future__ import annotations

from typing import Any

_MAX_KEYS = 20
_MAX_STR = 200
_BLOCKED = frozenset(
    {
        "content",
        "text",
        "ocr",
        "prompt",
        "api_key",
        "token",
        "password",
        "secret",
        "authorization",
        "signed_url",
        "path",
        "object_key",
        "stack",
        "traceback",
    }
)


def sanitize_processing_metadata(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(data.items()):
        if i >= _MAX_KEYS:
            break
        key = str(k)[:64].lower()
        if key in _BLOCKED or any(b in key for b in ("secret", "token", "password", "key")):
            continue
        if isinstance(v, str):
            out[str(k)[:64]] = v[:_MAX_STR]
        elif isinstance(v, (int, float, bool)) or v is None:
            out[str(k)[:64]] = v
        elif isinstance(v, dict):
            nested = sanitize_processing_metadata(v)
            if nested:
                out[str(k)[:64]] = nested
    return out or None


def sanitize_error_message(exc: BaseException | str | None, *, limit: int = 240) -> str:
    if exc is None:
        return ""
    raw = str(exc) if not isinstance(exc, str) else exc
    lower = raw.lower()
    for token in ("bearer ", "api_key", "service_role", "password"):
        if token in lower:
            return "error_sanitized"
    return raw.replace("\n", " ")[:limit]
