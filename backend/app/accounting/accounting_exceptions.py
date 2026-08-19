"""Exceptions Accounting Pipeline."""

from __future__ import annotations


class AccountingError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AccountingNotFoundError(AccountingError):
    def __init__(self, message: str = "Proposition introuvable"):
        super().__init__("not_found", message)


class AccountingDisabledError(AccountingError):
    def __init__(self, message: str = "Accounting Pipeline désactivé"):
        super().__init__("disabled", message)


class AccountingValidationError(AccountingError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class AccountingPermissionError(AccountingError):
    def __init__(self, message: str = "Permission refusée"):
        super().__init__("permission_denied", message)


class AccountingStateError(AccountingError):
    def __init__(self, message: str):
        super().__init__("invalid_state", message)
