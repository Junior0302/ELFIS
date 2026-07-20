"""Types et constantes notifications."""

from __future__ import annotations


class NotificationTypes:
    VAULT_DOCUMENT_ARCHIVED = "vault.document.archived"
    VAULT_DOCUMENT_REUSED = "vault.document.reused"

    DELIVERY_EMAIL_SENT = "delivery.email.sent"
    DELIVERY_EMAIL_FAILED = "delivery.email.failed"

    BILLING_DOCUMENT_SENT = "billing.document.sent"
    BILLING_DOCUMENT_SEND_FAILED = "billing.document.send_failed"

    SYSTEM_WELCOME = "system.welcome"
    SYSTEM_SECURITY_ALERT = "system.security_alert"

    SUBSCRIPTION_TRIAL_STARTED = "subscription.trial_started"
    SUBSCRIPTION_TRIAL_ENDING = "subscription.trial_ending"
    SUBSCRIPTION_PAYMENT_FAILED = "subscription.payment_failed"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"


class NotificationCategories:
    BILLING = "billing"
    VAULT = "vault"
    EMAIL = "email"
    ACCOUNTING = "accounting"
    SECURITY = "security"
    SUBSCRIPTION = "subscription"
    SYSTEM = "system"


class NotificationSeverity:
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationStatus:
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class NotificationChannel:
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class DeliveryStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class DigestMode:
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"
    DISABLED = "disabled"


# Template names
TEMPLATE_DOCUMENT_EMAIL_SENT = "document_email_sent"
TEMPLATE_DOCUMENT_EMAIL_FAILED = "document_email_failed"
TEMPLATE_DOCUMENT_ARCHIVED = "document_archived"
TEMPLATE_SYSTEM_GENERIC = "system_generic"
