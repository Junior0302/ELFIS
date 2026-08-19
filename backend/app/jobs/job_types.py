"""Noms de jobs centralisés."""

from __future__ import annotations


class JobNames:
    SYSTEM_HEALTH_CHECK = "system.health_check.v1"
    VAULT_DOCUMENT_METADATA_CHECK = "vault.document.metadata_check.v1"

    VAULT_DOCUMENT_EXTRACT_TEXT = "vault.document.extract_text.v1"
    VAULT_DOCUMENT_OCR = "vault.document.ocr.v1"
    VAULT_DOCUMENT_PREPARE_ANALYSIS = "vault.document.prepare_analysis.v1"

    VAULT_DOCUMENT_AI_CLASSIFICATION = "vault.document.ai_classification.v1"
    VAULT_DOCUMENT_AI_EXTRACTION = "vault.document.ai_extraction.v1"
    VAULT_DOCUMENT_QUALITY_CHECK = "vault.document.quality_check.v1"

    ACCOUNTING_BUILD_PROPOSAL = "accounting.build_proposal.v1"
    ACCOUNTING_REPROCESS_PROPOSAL = "accounting.reprocess_proposal.v1"
    ACCOUNTING_VALIDATE_MAPPING = "accounting.validate_mapping.v1"

    SEARCH_INDEX_RESOURCE = "search.index_resource.v1"
    SEARCH_REMOVE_RESOURCE = "search.remove_resource.v1"
    SEARCH_REINDEX_ORGANIZATION = "search.reindex_organization.v1"

    DOCUMENT_EXTRACTION_RUN = "document.extraction.run.v1"

    # Préparés — non exécutés
    VAULT_DOCUMENT_DRIVE_SYNC = "vault.document.drive_sync.v1"
    BILLING_GENERATE_REPORT = "billing.generate_report.v1"
    BILLING_TRIAL_REMINDERS = "billing.trial_reminders.v1"
    BILLING_SYNC_SUBSCRIPTION = "billing.sync_subscription.v1"
    ACCOUNTING_EXPORT_FEC = "accounting.export_fec.v1"
    NOTIFICATION_SEND_EMAIL = "notification.send_email.v1"

    RELIABILITY_CLEANUP_EXPIRED_RECORDS = "reliability.cleanup_expired_records.v1"
    RELIABILITY_CHECK_SYSTEM_HEALTH = "reliability.check_system_health.v1"
    RELIABILITY_DETECT_STALE_JOBS = "reliability.detect_stale_jobs.v1"
    RELIABILITY_DETECT_STALE_EVENTS = "reliability.detect_stale_events.v1"


IMPLEMENTED_JOB_NAMES: frozenset[str] = frozenset(
    {
        JobNames.SYSTEM_HEALTH_CHECK,
        JobNames.RELIABILITY_CLEANUP_EXPIRED_RECORDS,
        JobNames.RELIABILITY_CHECK_SYSTEM_HEALTH,
        JobNames.RELIABILITY_DETECT_STALE_JOBS,
        JobNames.RELIABILITY_DETECT_STALE_EVENTS,
        JobNames.VAULT_DOCUMENT_METADATA_CHECK,
        JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
        JobNames.VAULT_DOCUMENT_OCR,
        JobNames.VAULT_DOCUMENT_PREPARE_ANALYSIS,
        JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION,
        JobNames.VAULT_DOCUMENT_AI_EXTRACTION,
        JobNames.VAULT_DOCUMENT_QUALITY_CHECK,
        JobNames.ACCOUNTING_BUILD_PROPOSAL,
        JobNames.ACCOUNTING_REPROCESS_PROPOSAL,
        JobNames.ACCOUNTING_VALIDATE_MAPPING,
        JobNames.SEARCH_INDEX_RESOURCE,
        JobNames.SEARCH_REMOVE_RESOURCE,
        JobNames.SEARCH_REINDEX_ORGANIZATION,
        JobNames.DOCUMENT_EXTRACTION_RUN,
        JobNames.BILLING_TRIAL_REMINDERS,
        JobNames.BILLING_SYNC_SUBSCRIPTION,
    }
)

ALL_KNOWN_JOB_NAMES: frozenset[str] = frozenset(
    getattr(JobNames, name)
    for name in dir(JobNames)
    if name.isupper() and not name.startswith("_")
)


class JobStatus:
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    RETRY = "retry"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class AttemptStatus:
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


DEFAULT_QUEUE = "default"
