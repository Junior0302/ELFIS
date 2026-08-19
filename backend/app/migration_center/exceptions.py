"""Exceptions Migration Center."""

from __future__ import annotations


class MigrationCenterError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class MigrationNotFoundError(MigrationCenterError):
    pass


class MigrationAccessDeniedError(MigrationCenterError):
    pass


class MigrationValidationError(MigrationCenterError):
    pass


class MigrationConflictError(MigrationCenterError):
    pass
