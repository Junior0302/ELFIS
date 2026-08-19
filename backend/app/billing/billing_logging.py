"""Logging sécurisé Billing — délègue à la redaction centrale."""

from __future__ import annotations

import hashlib
from typing import Any

_FORBIDDEN_EXTRA = {
    "payload",
    "stripe_payload",
    "card",
    "cvc",
    "number",
    "api_key",
    "secret",
    "signature",
    "stripe_signature",
    "authorization",
    "password",
    "token",
    "prompt",
    "raw_text",
    "email_body",
}


def sanitize_billing_error(message: str | None, *, max_len: int = 500) -> str | None:
    from app.security.security_redaction import redact_string

    return redact_string(message, max_len=max_len)


def hash_provider_event_id(event_id: str | None) -> str | None:
    if not event_id:
        return None
    return hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:16]


def safe_billing_log_context(
    *,
    billing_event_id: str | None = None,
    provider_event_id: str | None = None,
    organization_id: int | None = None,
    subscription_id: str | None = None,
    plan_code: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
    processing_time_ms: int | None = None,
    idempotent_reuse: bool | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    from app.security.security_redaction import safe_log_context

    fields: dict[str, Any] = {}
    for key, val in {
        "billing_event_id": billing_event_id,
        "provider_event_hash": hash_provider_event_id(provider_event_id),
        "organization_id": organization_id,
        "subscription_id": subscription_id,
        "plan_code": plan_code,
        "status": status,
        "event_type": event_type,
        "processing_time_ms": processing_time_ms,
        "idempotent_reuse": idempotent_reuse,
        "correlation_id": correlation_id,
    }.items():
        if val is not None:
            fields[key] = val
    for k, v in extra.items():
        if k.lower() in _FORBIDDEN_EXTRA:
            continue
        fields[k] = v
    return safe_log_context(**fields)
