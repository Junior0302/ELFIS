"""Exceptions Accounting Engine V2."""

from __future__ import annotations


class AccountingEngineError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class EngineNotFoundError(AccountingEngineError):
    def __init__(self, message: str = "Proposition introuvable"):
        super().__init__("ae_not_found", message)


class EngineValidationError(AccountingEngineError):
    def __init__(self, message: str = "Données invalides"):
        super().__init__("ae_validation", message)


class EngineStateError(AccountingEngineError):
    def __init__(self, message: str = "État invalide"):
        super().__init__("ae_state", message)
