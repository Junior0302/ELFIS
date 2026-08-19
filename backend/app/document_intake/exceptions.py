"""Exceptions Document Intake."""

from __future__ import annotations


class DocumentIntakeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class DocumentIntakeNotFoundError(DocumentIntakeError):
    pass


class DocumentIntakeAccessDeniedError(DocumentIntakeError):
    pass


class DocumentIntakeValidationError(DocumentIntakeError):
    pass


class DocumentIntakeQuotaError(DocumentIntakeError):
    pass


class DocumentIntakeConflictError(DocumentIntakeError):
    pass
