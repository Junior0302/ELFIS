"""Exceptions Accounting Intelligence V2."""

from __future__ import annotations


class AccountingIntelligenceError(Exception):
    code = "accounting_intelligence_error"

    def __init__(self, message: str, *, code: str | None = None):
        self.message = message
        if code:
            self.code = code
        super().__init__(message)


class IntelligenceNotFoundError(AccountingIntelligenceError):
    code = "intelligence_not_found"


class IntelligenceValidationError(AccountingIntelligenceError):
    code = "intelligence_validation"


class IntelligenceStateError(AccountingIntelligenceError):
    code = "intelligence_state"
