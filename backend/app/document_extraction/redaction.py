"""Helpers de redaction — logs / events sans données sensibles."""

from __future__ import annotations

import re
from typing import Any

_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
_PATH = re.compile(r"(?:[A-Za-z]:\\|/)[^\s\"']+")


def redact_text(text: str) -> str:
    if not text:
        return text
    out = _IBAN.sub("[IBAN_REDACTED]", text)
    out = _EMAIL.sub("[EMAIL_REDACTED]", out)
    out = _PHONE.sub("[PHONE_REDACTED]", out)
    out = _PATH.sub("[PATH_REDACTED]", out)
    return out


def safe_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Copie filtrée — jamais de structured_data / texte / prompt."""
    allowed = {
        "event_id",
        "event_type",
        "organization_id",
        "migration_session_id",
        "document_intake_item_id",
        "universal_document_id",
        "extraction_id",
        "status",
        "schema_name",
        "schema_version",
        "overall_confidence",
        "requires_human_review",
        "actor_user_id",
        "occurred_at",
        "schema_version_event",
        "correlation_id",
        "metadata",
    }
    out = {k: payload.get(k) for k in allowed if k in payload}
    meta = out.get("metadata")
    if isinstance(meta, dict):
        out["metadata"] = {
            k: v
            for k, v in meta.items()
            if k
            in {
                "progress_percent",
                "current_step",
                "strategy",
                "error_code",
                "quota_code",
            }
        }
    return out


FORBIDDEN_LOG_KEYS = frozenset(
    {
        "text",
        "page_texts",
        "prompt",
        "system_prompt",
        "raw_response",
        "api_key",
        "iban",
        "structured_data",
        "line_items",
        "transactions",
    }
)


def assert_log_extra_safe(extra: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in extra.items() if k not in FORBIDDEN_LOG_KEYS}
