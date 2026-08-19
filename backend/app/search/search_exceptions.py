"""Exceptions Search Engine."""

from __future__ import annotations


class SearchError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class SearchDisabledError(SearchError):
    def __init__(self, message: str = "Search Engine désactivé"):
        super().__init__("disabled", message)


class SearchValidationError(SearchError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class SearchNotFoundError(SearchError):
    def __init__(self, message: str = "Document de recherche introuvable"):
        super().__init__("not_found", message)


class SearchPermissionError(SearchError):
    def __init__(self, message: str = "Permission refusée"):
        super().__init__("permission_denied", message)
