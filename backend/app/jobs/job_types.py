"""Noms de jobs centralisés."""

from __future__ import annotations


class JobNames:
    SYSTEM_HEALTH_CHECK = "system.health_check.v1"
    VAULT_DOCUMENT_METADATA_CHECK = "vault.document.metadata_check.v1"

    VAULT_DOCUMENT_AI_CLASSIFICATION = "vault.document.ai_classification.v1"
    VAULT_DOCUMENT_AI_EXTRACTION = "vault.document.ai_extraction.v1"
    VAULT_DOCUMENT_QUALITY_CHECK = "vault.document.quality_check.v1"

    # Préparés — non exécutés
    VAULT_DOCUMENT_OCR = "vault.document.ocr.v1"
    VAULT_DOCUMENT_DRIVE_SYNC = "vault.document.drive_sync.v1"
    BILLING_GENERATE_REPORT = "billing.generate_report.v1"
    ACCOUNTING_EXPORT_FEC = "accounting.export_fec.v1"
    NOTIFICATION_SEND_EMAIL = "notification.send_email.v1"


IMPLEMENTED_JOB_NAMES: frozenset[str] = frozenset(
    {
        JobNames.SYSTEM_HEALTH_CHECK,
        JobNames.VAULT_DOCUMENT_METADATA_CHECK,
        JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION,
        JobNames.VAULT_DOCUMENT_AI_EXTRACTION,
        JobNames.VAULT_DOCUMENT_QUALITY_CHECK,
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
