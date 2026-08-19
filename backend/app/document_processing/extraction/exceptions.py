"""Exceptions extraction."""

from __future__ import annotations


class ExtractionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ExtractionValidationError(ExtractionError):
    pass


class ExtractionAccessDeniedError(ExtractionError):
    pass


class ExtractionNotFoundError(ExtractionError):
    pass


class ExtractionRetryableError(ExtractionError):
    pass


class ExtractionPermanentError(ExtractionError):
    pass
