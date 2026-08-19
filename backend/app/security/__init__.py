"""ELFIS Security V1 — couche transverse."""

from __future__ import annotations

from app.security.security_exceptions import SecurityError, build_error_body, error_response
from app.security.security_file_validation import validate_uploaded_file
from app.security.security_permissions import require_permission
from app.security.security_redaction import (
    redact_mapping,
    redact_string,
    safe_exception_message,
    safe_log_context,
)
from app.security.security_types import ErrorCode, RateLimitCategory, SecurityEventType

__all__ = [
    "ErrorCode",
    "RateLimitCategory",
    "SecurityError",
    "SecurityEventType",
    "build_error_body",
    "error_response",
    "redact_mapping",
    "redact_string",
    "require_permission",
    "safe_exception_message",
    "safe_log_context",
    "validate_uploaded_file",
]
