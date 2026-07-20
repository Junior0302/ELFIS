"""Registry des handlers d'événements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.events.event_context import EventContext
    from app.events.event_schemas import DomainEvent


class EventHandler(ABC):
    """Handler synchrone (aligné SQLAlchemy / FastAPI sync)."""

    handler_name: str

    @abstractmethod
    def handle(self, event: DomainEvent, context: EventContext) -> None:
        raise NotImplementedError


class EventHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._by_name: dict[str, EventHandler] = {}

    def register(self, event_name: str, handler: EventHandler) -> None:
        name = (handler.handler_name or "").strip()
        if not name:
            raise ValueError("handler_name requis")
        if name in self._by_name and self._by_name[name] is not handler:
            raise ValueError(f"handler_name déjà enregistré: {name}")
        self._by_name[name] = handler
        bucket = self._handlers[event_name]
        if handler not in bucket:
            bucket.append(handler)

    def get_handlers(self, event_name: str) -> list[EventHandler]:
        return list(self._handlers.get(event_name, []))

    def all_handler_names(self) -> list[str]:
        return sorted(self._by_name.keys())

    def clear(self) -> None:
        self._handlers.clear()
        self._by_name.clear()


# Registry global applicatif (handlers métier enregistrés au démarrage)
default_registry = EventHandlerRegistry()
