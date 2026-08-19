"""Exceptions IAM — messages sûrs, sans secrets."""

from __future__ import annotations


class PermissionError(Exception):
    """Erreur de base du Permission Engine."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class UnknownPermissionError(PermissionError):
    def __init__(self, permission: str) -> None:
        super().__init__(
            "unknown_permission",
            "Permission inconnue",
        )
        self.permission = permission


class PermissionDeniedError(PermissionError):
    def __init__(self, permission: str | None = None) -> None:
        super().__init__(
            "permission_denied",
            "Accès refusé",
        )
        self.permission = permission


class AuthenticationRequiredError(PermissionError):
    def __init__(self) -> None:
        super().__init__(
            "authentication_required",
            "Authentification requise",
        )
