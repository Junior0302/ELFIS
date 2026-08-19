"""Exceptions Document Analysis."""

from __future__ import annotations


class DocumentAnalysisError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class DocumentAnalysisNotFoundError(DocumentAnalysisError):
    pass


class DocumentAnalysisConflictError(DocumentAnalysisError):
    pass


class DocumentAnalysisValidationError(DocumentAnalysisError):
    pass
