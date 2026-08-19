"""Exceptions validation métier."""

from __future__ import annotations


class BusinessValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class BusinessValidationAccessDeniedError(BusinessValidationError):
    pass


class BusinessValidationNotFoundError(BusinessValidationError):
    pass


class BusinessValidationValidationError(BusinessValidationError):
    pass
