"""Event Bus — abstraction + implémentation Database (V1)."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Iterable

from sqlalchemy.orm import Session

from app.config import settings
from app.events.event_models import ElfisEvent
from app.events.event_registry import EventHandler, EventHandlerRegistry, default_registry
from app.events.event_repository import EventRepository
from app.events.event_schemas import DomainEvent
from app.events.event_context import log_event, new_correlation_id, safe_event_log_context
from app.events.exceptions import (
    EventDuplicateError,
    EventPublishError,
    EventValidationError,
)

logger = logging.getLogger(__name__)


class EventBus(ABC):
    """Interface pour futures implémentations (Supabase Queue, Redis, RabbitMQ, Kafka…)."""

    @abstractmethod
    def publish(self, event: DomainEvent, *, commit: bool = True) -> ElfisEvent:
        raise NotImplementedError

    @abstractmethod
    def publish_many(
        self, events: Iterable[DomainEvent], *, commit: bool = True
    ) -> list[ElfisEvent]:
        raise NotImplementedError

    @abstractmethod
    def register_handler(self, event_name: str, handler: EventHandler) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_handlers(self, event_name: str) -> list[EventHandler]:
        raise NotImplementedError


class DatabaseEventBus(EventBus):
    """
    Bus durable basé sur PostgreSQL / SQLite.

    TODO architectural (outbox transactionnel) :
    Les services métier (VaultRepository, sales_email) commitent déjà
    leurs propres transactions. Une atomicité stricte métier+événement
    n'est donc PAS garantie sans refactor unit-of-work.
    La publication est best-effort après l'opération métier ; un échec
    de publish est journalisé et ne doit pas casser le flux utilisateur.
    """

    def __init__(
        self,
        db: Session,
        registry: EventHandlerRegistry | None = None,
        *,
        max_attempts: int | None = None,
    ):
        self._db = db
        self._registry = registry or default_registry
        self._repo = EventRepository(db)
        self._max_attempts = max_attempts or settings.elfis_event_max_attempts

    def register_handler(self, event_name: str, handler: EventHandler) -> None:
        self._registry.register(event_name, handler)

    def get_handlers(self, event_name: str) -> list[EventHandler]:
        return self._registry.get_handlers(event_name)

    def publish(self, event: DomainEvent, *, commit: bool = True) -> ElfisEvent:
        try:
            validated = DomainEvent.model_validate(event.model_dump())
        except Exception as exc:
            raise EventValidationError(str(exc)) from exc

        if not validated.correlation_id:
            validated.correlation_id = uuid.UUID(new_correlation_id())

        handlers = self._registry.get_handlers(validated.event_name)
        handler_names = [h.handler_name for h in handlers]

        try:
            row = self._repo.create_event_with_deliveries(
                validated,
                handler_names,
                max_attempts=self._max_attempts,
                commit=commit,
            )
        except EventDuplicateError as exc:
            log_event(
                logging.INFO,
                "event_publish_duplicate",
                event_name=validated.event_name,
                organization_id=validated.organization_id,
                correlation_id=str(validated.correlation_id),
                status="duplicate",
                extra={"existing_event_id": exc.existing_event_id},
            )
            if exc.existing_event_id:
                existing = self._repo.find_by_event_id(exc.existing_event_id)
                if existing:
                    return existing
            raise
        except EventPublishError:
            raise
        except Exception as exc:
            raise EventPublishError("Publication impossible") from exc

        log_event(
            logging.INFO,
            "event_published",
            event_id=row.event_id,
            event_name=row.event_name,
            organization_id=row.organization_id,
            correlation_id=row.correlation_id,
            status=row.status,
            extra={"handler_count": len(handler_names)},
        )
        return row

    def publish_many(
        self, events: Iterable[DomainEvent], *, commit: bool = True
    ) -> list[ElfisEvent]:
        rows: list[ElfisEvent] = []
        for event in events:
            rows.append(self.publish(event, commit=commit))
        return rows


def get_event_bus(db: Session) -> DatabaseEventBus:
    return DatabaseEventBus(db)


def safe_publish(
    db: Session,
    event: DomainEvent,
    *,
    commit: bool = True,
) -> ElfisEvent | None:
    """Publication non bloquante pour les flux métier existants."""
    try:
        return get_event_bus(db).publish(event, commit=commit)
    except EventDuplicateError as exc:
        logger.info(
            "event_safe_publish_duplicate",
            extra=safe_event_log_context(
                event_name=event.event_name,
                organization_id=event.organization_id,
                extra={"existing_event_id": exc.existing_event_id},
            ),
        )
        if exc.existing_event_id:
            return EventRepository(db).find_by_event_id(exc.existing_event_id)
        return None
    except Exception:
        logger.exception(
            "event_safe_publish_failed",
            extra=safe_event_log_context(
                event_name=event.event_name,
                organization_id=event.organization_id,
                correlation_id=str(event.correlation_id) if event.correlation_id else None,
            ),
        )
        return None
