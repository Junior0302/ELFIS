"""Exceptions product integrations."""

from __future__ import annotations


class ProductIntegrationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ProductIntegrationNotFoundError(ProductIntegrationError):
    pass


class ProductIntegrationAccessDeniedError(ProductIntegrationError):
    pass


class ProductIntegrationValidationError(ProductIntegrationError):
    pass


class ProductBridgeDisabledError(ProductIntegrationValidationError):
    pass
