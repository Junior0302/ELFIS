"""Exceptions classification."""

from __future__ import annotations


class ClassificationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ClassificationValidationError(ClassificationError):
    pass


class ClassificationAccessDeniedError(ClassificationError):
    pass


class ClassificationNotFoundError(ClassificationError):
    pass
