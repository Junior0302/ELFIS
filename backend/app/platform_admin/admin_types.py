"""Types Platform Admin."""

from __future__ import annotations


class OrgPlatformStatus:
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RESTRICTED = "restricted"
    CLOSED = "closed"


class AdminAuditStatus:
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"


class IncidentSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IncidentStatus:
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class IncidentTypes:
    JOB_DEAD_LETTER = "job_dead_letter"
    EVENT_DEAD_LETTER = "event_dead_letter"
    DELIVERY_FAILED = "delivery_failed"
    AI_FAILED = "ai_failed"
    DOCUMENT_REQUIRES_OCR = "document_requires_ocr"
    ACCOUNTING_UNBALANCED = "accounting_unbalanced"
    BILLING_PAYMENT_FAILED = "billing_payment_failed"
    BILLING_SYNC_FAILED = "billing_sync_failed"
    SEARCH_INDEX_FAILED = "search_index_failed"


class AdminPermissions:
    """Structure préparatoire — V1 : tous couverts par require_platform_admin."""

    DASHBOARD_VIEW = "platform.dashboard.view"
    ORGANIZATIONS_VIEW = "platform.organizations.view"
    ORGANIZATIONS_MANAGE = "platform.organizations.manage"
    USERS_VIEW = "platform.users.view"
    USERS_MANAGE = "platform.users.manage"
    BILLING_VIEW = "platform.billing.view"
    BILLING_MANAGE = "platform.billing.manage"
    JOBS_VIEW = "platform.jobs.view"
    JOBS_MANAGE = "platform.jobs.manage"
    EVENTS_VIEW = "platform.events.view"
    EVENTS_MANAGE = "platform.events.manage"
    AI_VIEW = "platform.ai.view"
    DOCUMENTS_VIEW = "platform.documents.view"
    ACCOUNTING_VIEW = "platform.accounting.view"
    INCIDENTS_VIEW = "platform.incidents.view"
    INCIDENTS_MANAGE = "platform.incidents.manage"
    AUDIT_VIEW = "platform.audit.view"


class ServiceHealthStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


# Champs autorisés dans previous_state / new_state
ALLOWED_STATE_KEYS: frozenset[str] = frozenset(
    {
        "status",
        "platform_status",
        "feature_code",
        "is_enabled",
        "quota_code",
        "limit_value",
        "plan_code",
        "subscription_status",
        "incident_status",
        "job_status",
        "event_status",
        "user_status",
        "reason_public",
    }
)

FORBIDDEN_ADMIN_RESPONSE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "stripe_secret",
        "openai",
        "authorization",
        "encrypted_access_token",
        "encrypted_refresh_token",
        "encrypted_smtp_password",
        "pdf",
        "pdf_bytes",
        "extracted_text",
        "prompt",
        "raw_response",
    }
)
