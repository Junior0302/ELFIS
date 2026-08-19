"""Rapport d'erreurs filtré — pas de stack en production."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.observability.metrics import metrics_registry
from app.observability.request_context import current_context
from app.security.security_redaction import safe_exception_message, safe_log_context

logger = logging.getLogger("elfis.error_reporting")


def report_error(
    exc: BaseException,
    *,
    error_code: str = "internal_error",
    event_type: str = "unhandled_exception",
    **fields: Any,
) -> dict[str, Any]:
    ctx = current_context()
    payload = safe_log_context(
        event_type=event_type,
        error_code=error_code,
        error_type=type(exc).__name__,
        message=safe_exception_message(exc),
        **ctx,
        **fields,
    )
    if settings.app_env.lower() != "production":
        payload["debug_message"] = safe_exception_message(exc, max_len=500)
    metrics_registry.incr("errors_reported_total", labels={"code": error_code})
    logger.error(event_type, extra={"elfis": payload})
    return payload
