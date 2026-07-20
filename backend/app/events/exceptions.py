"""Exceptions Event Bus."""

from __future__ import annotations


class EventBusError(Exception):
    """Erreur générique du bus."""


class EventValidationError(EventBusError):
    """Événement invalide (payload / champs requis)."""


class EventPublishError(EventBusError):
    """Échec de persistance / publication."""


class EventHandlerError(EventBusError):
    """Erreur levée / wrappée par un handler."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class EventDuplicateError(EventBusError):
    """Publication rejetée pour cause d'idempotence."""

    def __init__(self, message: str, *, existing_event_id: str | None = None):
        super().__init__(message)
        self.existing_event_id = existing_event_id
