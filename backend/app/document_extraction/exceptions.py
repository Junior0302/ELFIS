"""Exceptions Document Extraction."""

from __future__ import annotations


class DocumentExtractionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class DocumentExtractionNotFoundError(DocumentExtractionError):
    pass


class DocumentExtractionConflictError(DocumentExtractionError):
    pass


class DocumentExtractionValidationError(DocumentExtractionError):
    pass


class DocumentExtractionQuotaError(DocumentExtractionError):
    pass


class DocumentExtractionIneligibleError(DocumentExtractionError):
    pass
