"""ELFIS Observability V1."""

from __future__ import annotations

from app.observability.correlation import ensure_correlation_id, inject_correlation
from app.observability.health import details, live, ready
from app.observability.metrics import metrics_registry
from app.observability.request_context import (
    bind_request_ids,
    clear_request_context,
    current_context,
    get_correlation_id,
    get_request_id,
    normalize_id_header,
    normalize_optional_id,
)
from app.observability.structured_logging import configure_structured_logging, log_event

__all__ = [
    "bind_request_ids",
    "clear_request_context",
    "configure_structured_logging",
    "current_context",
    "details",
    "ensure_correlation_id",
    "get_correlation_id",
    "get_request_id",
    "inject_correlation",
    "live",
    "log_event",
    "metrics_registry",
    "normalize_id_header",
    "ready",
]
