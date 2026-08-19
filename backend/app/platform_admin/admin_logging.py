"""Logging sécurisé Platform Admin."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_SECRET_RE = re.compile(
    r"(?i)(sk_live_|sk_test_|whsec_|api[_-]?key|token|password|secret|authorization)[=:\s]*[^\s,;]+"
)


def sanitize_admin_text(message: str | None, *, max_len: int = 400) -> str | None:
    if message is None:
        return None
    cleaned = _SECRET_RE.sub("***", str(message))
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def safe_admin_log_context(
    *,
    actor_user_id: int | None = None,
    organization_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    status: str | None = None,
    duration_ms: int | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for key, val in {
        "actor_user_id": actor_user_id,
        "organization_id": organization_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "status": status,
        "duration_ms": duration_ms,
        "request_id": request_id,
        "correlation_id": correlation_id,
    }.items():
        if val is not None:
            ctx[key] = val
    forbidden = {
        "reason",
        "password",
        "token",
        "secret",
        "payload",
        "document",
        "email_body",
        "stripe_payload",
        "prompt",
    }
    for k, v in extra.items():
        if k.lower() in forbidden:
            continue
        ctx[k] = v
    return ctx
