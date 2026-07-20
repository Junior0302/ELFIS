"""Noms d'événements centralisés — convention module.entity.action.vN."""

from __future__ import annotations


class EventNames:
    """Constantes stables pour le bus (pas de chaînes dispersées)."""

    VAULT_DOCUMENT_ARCHIVED = "vault.document.archived.v1"
    VAULT_DOCUMENT_REUSED = "vault.document.reused.v1"

    DELIVERY_EMAIL_STARTED = "delivery.email.started.v1"
    DELIVERY_EMAIL_SENT = "delivery.email.sent.v1"
    DELIVERY_EMAIL_FAILED = "delivery.email.failed.v1"

    # Préparés — pas encore publiés systématiquement
    BILLING_INVOICE_CREATED = "billing.invoice.created.v1"
    BILLING_INVOICE_SENT = "billing.invoice.sent.v1"
    BILLING_QUOTE_SENT = "billing.quote.sent.v1"
    BILLING_CREDIT_NOTE_SENT = "billing.credit_note.sent.v1"

    NOTIFICATION_CREATED = "notification.created.v1"
    NOTIFICATION_EMAIL_REQUESTED = "notification.email.requested.v1"
    NOTIFICATION_EMAIL_SENT = "notification.email.sent.v1"
    NOTIFICATION_EMAIL_FAILED = "notification.email.failed.v1"
    NOTIFICATION_READ = "notification.read.v1"

    JOB_CREATED = "job.created.v1"
    JOB_STARTED = "job.started.v1"
    JOB_PROGRESS = "job.progress.v1"
    JOB_COMPLETED = "job.completed.v1"
    JOB_RETRY_SCHEDULED = "job.retry_scheduled.v1"
    JOB_FAILED = "job.failed.v1"
    JOB_DEAD_LETTERED = "job.dead_lettered.v1"
    JOB_CANCELLED = "job.cancelled.v1"
    JOB_TIMED_OUT = "job.timed_out.v1"
    JOB_RETRIED = "job.retried.v1"

    AI_EXECUTION_CREATED = "ai.execution.created.v1"
    AI_EXECUTION_STARTED = "ai.execution.started.v1"
    AI_EXECUTION_COMPLETED = "ai.execution.completed.v1"
    AI_EXECUTION_FAILED = "ai.execution.failed.v1"
    AI_EXECUTION_REQUIRES_REVIEW = "ai.execution.requires_review.v1"
    AI_USAGE_RECORDED = "ai.usage.recorded.v1"
    DOCUMENT_ANALYSIS_COMPLETED = "document.analysis.completed.v1"


ALL_KNOWN_EVENT_NAMES: frozenset[str] = frozenset(
    getattr(EventNames, name)
    for name in dir(EventNames)
    if name.isupper() and not name.startswith("_")
)
