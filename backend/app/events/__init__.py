"""ELFIS Event Bus V1 — publication durable + worker DB."""

from __future__ import annotations

from app.events.event_bus import DatabaseEventBus, EventBus, get_event_bus, safe_publish
from app.events.event_registry import EventHandler, EventHandlerRegistry, default_registry
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.event_worker import EventWorker, compute_retry_delay_seconds


_handlers_bootstrapped = False


def bootstrap_handlers(registry: EventHandlerRegistry | None = None) -> None:
    """Enregistre les handlers applicatifs (idempotent)."""
    global _handlers_bootstrapped
    reg = registry or default_registry
    if registry is None and _handlers_bootstrapped:
        return
    from app.events.handlers.document_handlers import DocumentArchivedAuditHandler
    from app.jobs.handlers.event_bridge import DocumentArchivedMetadataJobHandler
    from app.notifications import register_notification_handlers
    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()

    handler = DocumentArchivedAuditHandler()
    existing = [
        h
        for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)
        if h.handler_name == handler.handler_name
    ]
    if not existing:
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, handler)

    meta_handler = DocumentArchivedMetadataJobHandler()
    meta_existing = [
        h
        for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)
        if h.handler_name == meta_handler.handler_name
    ]
    if not meta_existing:
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, meta_handler)

    register_notification_handlers(reg)

    if registry is None:
        _handlers_bootstrapped = True


__all__ = [
    "DatabaseEventBus",
    "DomainEvent",
    "EventBus",
    "EventHandler",
    "EventHandlerRegistry",
    "EventNames",
    "EventWorker",
    "bootstrap_handlers",
    "compute_retry_delay_seconds",
    "default_registry",
    "get_event_bus",
    "safe_publish",
]
