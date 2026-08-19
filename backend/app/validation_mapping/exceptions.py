"""Exceptions Validation & Mapping."""

from __future__ import annotations


class ValidationMappingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ValidationNotFoundError(ValidationMappingError):
    pass


class ValidationConflictError(ValidationMappingError):
    pass


class ValidationPermissionError(ValidationMappingError):
    pass


class ValidationStateError(ValidationMappingError):
    pass
