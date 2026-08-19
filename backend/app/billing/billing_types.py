"""Types Billing — plans, features, quotas, usage."""

from __future__ import annotations


class PlanCodes:
    FREE_TRIAL = "free_trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingIntervals:
    MONTH = "month"
    YEAR = "year"
    ONE_TIME = "one_time"
    NONE = "none"


class SubscriptionStatus:
    INCOMPLETE = "incomplete"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


STRIPE_STATUS_MAP: dict[str, str] = {
    "incomplete": SubscriptionStatus.INCOMPLETE,
    "incomplete_expired": SubscriptionStatus.EXPIRED,
    "trialing": SubscriptionStatus.TRIALING,
    "active": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "unpaid": SubscriptionStatus.UNPAID,
    "paused": SubscriptionStatus.PAUSED,
    "canceled": SubscriptionStatus.CANCELLED,
    "cancelled": SubscriptionStatus.CANCELLED,
}


class FeatureCodes:
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_VAULT = "documents.vault"
    DOCUMENTS_TEXT_EXTRACTION = "documents.text_extraction"
    DOCUMENTS_OCR = "documents.ocr"
    AI_CLASSIFICATION = "ai.classification"
    AI_INVOICE_EXTRACTION = "ai.invoice_extraction"
    AI_QUALITY_CHECK = "ai.quality_check"
    ACCOUNTING_PROPOSALS = "accounting.proposals"
    ACCOUNTING_VALIDATION = "accounting.validation"
    ACCOUNTING_EXPORT = "accounting.export"
    SEARCH_GLOBAL = "search.global"
    EMAIL_SEND = "email.send"
    NOTIFICATIONS_IN_APP = "notifications.in_app"
    PLATFORM_CUSTOM_EMAIL = "platform.custom_email"
    USERS_MULTI_USER = "users.multi_user"
    ORGANIZATIONS_MULTI_ENTITY = "organizations.multi_entity"
    API_ACCESS = "api.access"
    # Préparés
    BANKING_SYNC = "banking.sync"
    ACCOUNTING_FEC_EXPORT = "accounting.fec_export"
    ACCOUNTING_EXPERT_ACCESS = "accounting.expert_access"
    AUTOMATION_ADVANCED = "automation.advanced"
    SUPPORT_PRIORITY = "support.priority"


class UsageCodes:
    DOCUMENTS_PROCESSED = "documents.processed"
    DOCUMENTS_STORED = "documents.stored"
    AI_EXECUTIONS = "ai.executions"
    AI_TOKENS = "ai.tokens"
    EMAILS_SENT = "emails.sent"
    ACCOUNTING_PROPOSALS = "accounting.proposals"
    SEARCH_QUERIES = "search.queries"
    STORAGE_BYTES = "storage.bytes"
    ORGANIZATION_USERS = "organization.users"


class QuotaCodes:
    DOCUMENTS_PROCESSED_MONTH = "documents.processed.month"
    AI_EXECUTIONS_MONTH = "ai.executions.month"
    AI_TOKENS_MONTH = "ai.tokens.month"
    EMAILS_SENT_MONTH = "emails.sent.month"
    STORAGE_BYTES = "storage.bytes"
    ORGANIZATION_USERS = "organization.users"


class EntitlementSources:
    PLAN = "plan"
    OVERRIDE = "override"
    TRIAL = "trial"
    PROMOTION = "promotion"
    PLATFORM_ADMIN = "platform_admin"


class QuotaPeriods:
    DAY = "day"
    MONTH = "month"
    BILLING_PERIOD = "billing_period"
    LIFETIME = "lifetime"


class BillingEventStatus:
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


# Features coûteuses bloquées après suspension / fin de grâce
COSTLY_FEATURES_WHEN_SUSPENDED: frozenset[str] = frozenset(
    {
        FeatureCodes.DOCUMENTS_UPLOAD,
        FeatureCodes.DOCUMENTS_TEXT_EXTRACTION,
        FeatureCodes.DOCUMENTS_OCR,
        FeatureCodes.AI_CLASSIFICATION,
        FeatureCodes.AI_INVOICE_EXTRACTION,
        FeatureCodes.AI_QUALITY_CHECK,
        FeatureCodes.ACCOUNTING_PROPOSALS,
        FeatureCodes.EMAIL_SEND,
        FeatureCodes.SEARCH_GLOBAL,
    }
)

# Features toujours consultables
READ_FEATURES: frozenset[str] = frozenset(
    {
        FeatureCodes.DOCUMENTS_VAULT,
        FeatureCodes.NOTIFICATIONS_IN_APP,
        FeatureCodes.ACCOUNTING_VALIDATION,  # consultation propositions
    }
)
