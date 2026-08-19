"""Sanitisation centrale — aucun secret dans elfis_audit_events."""

from __future__ import annotations

from typing import Any, Mapping

from app.security.security_redaction import redact_mapping, redact_string

# Clés / fragments explicitement refusés même après redaction partielle
_BLOCKED_METADATA_KEYS = frozenset(
    {
        "jwt",
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "access_token",
        "refresh_token",
        "id_token",
        "cookie",
        "cookies",
        "stripe_token",
        "stripe_signature",
        "whsec",
        "vault_secret",
        "private_key",
        "ocr_text",
        "raw_text",
        "prompt",
        "completion",
        "ai_response",
        "full_text",
        "physical_path",
        "file_path",
        "local_path",
        "storage_path",
        "filepath",
        "file_content",
        "file_bytes",
    }
)


def sanitize_message(message: str | None, *, max_len: int = 2000) -> str | None:
    if message is None:
        return None
    return redact_string(str(message), max_len=max_len)


def sanitize_user_agent(user_agent: str | None, *, max_len: int = 512) -> str | None:
    if not user_agent:
        return None
    return redact_string(str(user_agent), max_len=max_len)


def sanitize_ip(ip: str | None, *, max_len: int = 64) -> str | None:
    if not ip:
        return None
    cleaned = str(ip).strip()[:max_len]
    return cleaned or None


def sanitize_metadata(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    filtered: dict[str, Any] = {}
    for key, value in data.items():
        k = str(key)
        lowered = k.lower().replace("-", "_")
        if lowered in _BLOCKED_METADATA_KEYS or any(b in lowered for b in _BLOCKED_METADATA_KEYS):
            continue
        filtered[k] = value
    redacted = redact_mapping(filtered)
    return redacted or None


def assert_no_secrets_in_payload(payload: Mapping[str, Any]) -> bool:
    """Utilitaire tests — True si aucun fragment sensible détecté en clair."""
    blob = str(payload).lower()
    forbidden = (
        "bearer ",
        "sk_live_",
        "sk_test_",
        "whsec_",
        "password=",
        "-----begin",
    )
    return not any(f in blob for f in forbidden)
