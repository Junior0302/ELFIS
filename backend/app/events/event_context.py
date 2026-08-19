"""Contexte d'exécution handlers + helpers d'observabilité."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_SECRET_PATTERNS = (
    re.compile(r"xkeysib-[a-zA-Z0-9_-]+", re.I),
    re.compile(r"xsmtpsib-[a-zA-Z0-9_-]+", re.I),
    re.compile(r"sk_(?:live|test)_[a-zA-Z0-9_-]+", re.I),
    re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization|bearer|jwt)[=:\s]+[^\s,;]+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
)


@dataclass
class EventContext:
    """Contexte d'exécution passé aux handlers."""

    db: Any
    worker_id: str
    attempt_count: int = 0
    delivery_id: str | None = None
    correlation_id: str | None = None
    organization_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def sanitize_error_message(exc: BaseException | str, *, max_len: int = 500) -> str:
    """Version nettoyée d'une erreur (pas de token / clé / PDF)."""
    if isinstance(exc, BaseException):
        text = f"{type(exc).__name__}: {exc}"
    else:
        text = str(exc)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    lowered = text.lower()
    for token in ("%pdf", "service_role", "api_key", "password=", "authorization:"):
        if token in lowered:
            text = text.replace(token, "[REDACTED]")
            text = text.replace(token.upper(), "[REDACTED]")
            text = text.replace(token.title(), "[REDACTED]")
    return text[:max_len]


def safe_event_log_context(
    *,
    event_id: str | None = None,
    event_name: str | None = None,
    handler_name: str | None = None,
    organization_id: int | None = None,
    correlation_id: str | None = None,
    attempt_count: int | None = None,
    worker_id: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Contexte de log structuré sans secrets."""
    ctx: dict[str, Any] = {}
    if event_id:
        ctx["event_id"] = event_id
    if event_name:
        ctx["event_name"] = event_name
    if handler_name:
        ctx["handler_name"] = handler_name
    if organization_id is not None:
        ctx["organization_id"] = organization_id
    if correlation_id:
        ctx["correlation_id"] = correlation_id
    if attempt_count is not None:
        ctx["attempt_count"] = attempt_count
    if worker_id:
        ctx["worker_id"] = worker_id
    if status:
        ctx["status"] = status
    if duration_ms is not None:
        ctx["duration_ms"] = round(duration_ms, 2)
    if extra:
        forbidden = {
            "payload",
            "pdf",
            "pdf_bytes",
            "token",
            "api_key",
            "service_role_key",
            "signed_url",
            "authorization",
        }
        for key, value in extra.items():
            if key.lower() in forbidden:
                continue
            ctx[key] = value
    return ctx


def log_event(
    level: int,
    message: str,
    **kwargs: Any,
) -> None:
    logger.log(level, message, extra=safe_event_log_context(**kwargs))
