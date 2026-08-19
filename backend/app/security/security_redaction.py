"""Redaction centrale — secrets, tokens, prompts, payloads."""

from __future__ import annotations

import re
from typing import Any, Mapping

from app.security.security_types import SENSITIVE_KEY_FRAGMENTS

_REDACTED = "***"
_SECRET_VALUE_RE = re.compile(
    r"(?i)(sk_live_|sk_test_|whsec_|Bearer\s+|api[_-]?key|token|password|secret|authorization)"
    r"[=:\s]*[^\s,;\"']+"
)


def _key_is_sensitive(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(frag in lowered for frag in SENSITIVE_KEY_FRAGMENTS)


def redact_string(value: str | None, *, max_len: int = 500) -> str | None:
    if value is None:
        return None
    cleaned = _SECRET_VALUE_RE.sub(_REDACTED, str(value))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def safe_exception_message(exc: BaseException | str | None, *, max_len: int = 300) -> str:
    if exc is None:
        return "error"
    text = str(exc)
    return redact_string(text, max_len=max_len) or "error"


def redact_mapping(data: Mapping[str, Any] | None, *, max_depth: int = 4) -> dict[str, Any]:
    if not data:
        return {}
    return _redact_value(dict(data), depth=0, max_depth=max_depth)  # type: ignore[return-value]


def _redact_value(value: Any, *, depth: int, max_depth: int) -> Any:
    if depth > max_depth:
        return _REDACTED
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if _key_is_sensitive(key):
                out[key] = _REDACTED
            else:
                out[key] = _redact_value(v, depth=depth + 1, max_depth=max_depth)
        return out
    if isinstance(value, (list, tuple)):
        return [_redact_value(v, depth=depth + 1, max_depth=max_depth) for v in value[:50]]
    if isinstance(value, str):
        return redact_string(value, max_len=500)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_string(str(value), max_len=200)


def safe_log_context(**fields: Any) -> dict[str, Any]:
    """Contexte de log filtré — API publique pour les modules métier."""
    return redact_mapping(fields)


def filter_error_details(details: Mapping[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    forbidden = {
        "traceback",
        "stack",
        "sql",
        "query",
        "password",
        "token",
        "secret",
        "authorization",
        "api_key",
        "stripe_signature",
    }
    out: dict[str, Any] = {}
    for k, v in details.items():
        if str(k).lower() in forbidden or _key_is_sensitive(str(k)):
            continue
        if isinstance(v, str) and len(v) > 500:
            out[str(k)] = v[:497] + "..."
        else:
            out[str(k)] = v
    return out
