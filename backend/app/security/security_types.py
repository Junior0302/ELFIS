"""Types et codes stables — Security V1."""

from __future__ import annotations

from enum import Enum


class ErrorCode:
    AUTHENTICATION_REQUIRED = "authentication_required"
    INVALID_TOKEN = "invalid_token"
    PERMISSION_DENIED = "permission_denied"
    ORGANIZATION_REQUIRED = "organization_required"
    ORGANIZATION_NOT_FOUND = "organization_not_found"
    ORGANIZATION_SUSPENDED = "organization_suspended"
    FEATURE_NOT_AVAILABLE = "feature_not_available"
    QUOTA_EXCEEDED = "quota_exceeded"
    RESOURCE_NOT_FOUND = "resource_not_found"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
    PLATFORM_ADMIN_REQUIRED = "platform_admin_required"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    INVALID_HEADER = "invalid_header"
    CROSS_TENANT_DENIED = "cross_tenant_denied"


class RateLimitCategory(str, Enum):
    AUTH = "auth"
    UPLOAD = "upload"
    AI = "ai"
    SEARCH = "search"
    EMAIL = "email"
    BILLING = "billing"
    PLATFORM_ADMIN = "platform_admin"
    WEBHOOK = "webhook"
    DEFAULT = "default"


class SecurityEventType(str, Enum):
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_WEBHOOK_SIGNATURE = "invalid_webhook_signature"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    SUSPICIOUS_FILE = "suspicious_file"
    CONFIGURATION_WARNING = "configuration_warning"
    SECRET_REDACTED = "secret_redacted"
    CROSS_TENANT_ACCESS_ATTEMPT = "cross_tenant_access_attempt"


class SecuritySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


MAX_REQUEST_ID_LEN = 64
REQUEST_ID_PATTERN = r"^[A-Za-z0-9._-]{8,64}$"

SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "stripe_signature",
    "card",
    "cvc",
    "iban",
    "account_number",
    "signed_url",
    "storage_key",
    "prompt",
    "raw_text",
    "email_body",
    "private_key",
    "webhook_secret",
)
