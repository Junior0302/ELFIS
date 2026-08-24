"""Exceptions Storage / Document Registry."""

from __future__ import annotations


class StorageError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(self.message)


class StorageValidationError(StorageError):
    pass


class StorageNotFoundError(StorageError):
    pass


class StorageProviderError(StorageError):
    pass


class StorageDisabledError(StorageError):
    pass


class DocumentNotFoundError(StorageError):
    pass


class DocumentAccessDeniedError(StorageError):
    pass
