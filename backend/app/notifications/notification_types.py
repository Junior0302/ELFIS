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

    BILLING_TRIAL_STARTED = "billing.trial.started"
    BILLING_TRIAL_ENDING = "billing.trial.ending"
    BILLING_TRIAL_EXPIRED = "billing.trial.expired"
    BILLING_SUBSCRIPTION_ACTIVE = "billing.subscription.active"
    BILLING_PAYMENT_SUCCEEDED = "billing.payment.succeeded"
    BILLING_PAYMENT_FAILED = "billing.payment.failed"
    BILLING_SUBSCRIPTION_PAST_DUE = "billing.subscription.past_due"
    BILLING_SUBSCRIPTION_CANCEL_SCHEDULED = "billing.subscription.cancel_scheduled"
    BILLING_SUBSCRIPTION_CANCELLED = "billing.subscription.cancelled"
    BILLING_SUBSCRIPTION_SUSPENDED = "billing.subscription.suspended"
    BILLING_SUBSCRIPTION_REACTIVATED = "billing.subscription.reactivated"
    BILLING_PLAN_CHANGED = "billing.plan.changed"
    BILLING_QUOTA_WARNING = "billing.quota.warning"
    BILLING_QUOTA_EXCEEDED = "billing.quota.exceeded"

    ACCOUNTING_PROPOSAL_READY = "accounting.proposal.ready"
    ACCOUNTING_PROPOSAL_REQUIRES_REVIEW = "accounting.proposal.requires_review"
    ACCOUNTING_PROPOSAL_VALIDATED = "accounting.proposal.validated"
    ACCOUNTING_PROPOSAL_REJECTED = "accounting.proposal.rejected"
    ACCOUNTING_PROPOSAL_FAILED = "accounting.proposal.failed"

    BANKING_CONSENT_EXPIRING = "banking.consent.expiring"
    BANKING_REAUTHENTICATION_REQUIRED = "banking.reauthentication.required"
    BANKING_CONNECTION_REAUTHENTICATED = "banking.connection.reauthenticated"
    BANKING_CONNECTION_REVOKED = "banking.connection.revoked"


class NotificationCategories:
    BILLING = "billing"
    VAULT = "vault"
    EMAIL = "email"
    ACCOUNTING = "accounting"
    BANKING = "banking"
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
TEMPLATE_ACCOUNTING_PROPOSAL_READY = "accounting_proposal_ready"
TEMPLATE_ACCOUNTING_PROPOSAL_REVIEW = "accounting_proposal_review"
TEMPLATE_ACCOUNTING_PROPOSAL_VALIDATED = "accounting_proposal_validated"
TEMPLATE_ACCOUNTING_PROPOSAL_REJECTED = "accounting_proposal_rejected"
TEMPLATE_ACCOUNTING_PROPOSAL_FAILED = "accounting_proposal_failed"
