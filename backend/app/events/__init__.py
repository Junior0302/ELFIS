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

    handler = DocumentArchivedAuditHandler()
    # Évite double register sur le registry global
    existing = [h for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED) if h.handler_name == handler.handler_name]
    if not existing:
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, handler)
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
