"""Exceptions Platform Admin."""

from __future__ import annotations


class AdminError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AdminValidationError(AdminError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class AdminNotFoundError(AdminError):
    def __init__(self, message: str = "Ressource introuvable"):
        super().__init__("not_found", message)


class AdminPermissionError(AdminError):
    def __init__(self, message: str = "Action plateforme refusée"):
        super().__init__("platform_admin_required", message)


class AdminActionDeniedError(AdminError):
    def __init__(self, message: str):
        super().__init__("action_denied", message)
