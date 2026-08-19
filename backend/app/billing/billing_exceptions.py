"""Exceptions Billing."""

from __future__ import annotations


class BillingError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class BillingDisabledError(BillingError):
    def __init__(self, message: str = "Billing désactivé"):
        super().__init__("billing_disabled", message)


class FeatureNotAvailableError(BillingError):
    def __init__(self, feature_code: str, message: str | None = None):
        self.feature_code = feature_code
        super().__init__(
            "feature_not_available",
            message or f"Fonctionnalité non disponible: {feature_code}",
        )


class QuotaExceededError(BillingError):
    def __init__(self, quota_code: str, message: str | None = None):
        self.quota_code = quota_code
        super().__init__(
            "quota_exceeded",
            message or f"Quota dépassé: {quota_code}",
        )


class BillingValidationError(BillingError):
    def __init__(self, message: str):
        super().__init__("validation_error", message)


class BillingNotFoundError(BillingError):
    def __init__(self, message: str = "Ressource billing introuvable"):
        super().__init__("not_found", message)


class BillingPermissionError(BillingError):
    def __init__(self, message: str = "Permission refusée"):
        super().__init__("permission_denied", message)


class StripeWebhookError(BillingError):
    def __init__(self, message: str):
        super().__init__("webhook_error", message)
