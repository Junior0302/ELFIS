"""Exceptions Smart Migration."""

from __future__ import annotations


class SmartMigrationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class SmartNotFoundError(SmartMigrationError):
    def __init__(self, message: str = "Ressource introuvable"):
        super().__init__("smart_not_found", message)


class SmartStateError(SmartMigrationError):
    def __init__(self, message: str = "État invalide"):
        super().__init__("smart_state_invalid", message)


class SmartConflictError(SmartMigrationError):
    def __init__(self, message: str = "Conflit"):
        super().__init__("smart_conflict", message)


class SmartConfirmationRequiredError(SmartMigrationError):
    def __init__(self, message: str = "Confirmation requise"):
        super().__init__("confirmation_required", message)
