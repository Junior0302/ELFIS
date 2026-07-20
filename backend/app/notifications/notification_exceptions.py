"""Exceptions Notification Service."""

from __future__ import annotations


class NotificationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class NotificationValidationError(NotificationError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class NotificationNotFoundError(NotificationError):
    def __init__(self, message: str = "Notification introuvable"):
        super().__init__("not_found", message)


class NotificationDuplicateError(NotificationError):
    def __init__(self, message: str, *, existing_id: str | None = None):
        self.existing_id = existing_id
        super().__init__("duplicate", message)
