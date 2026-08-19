"""Enums Import Engine."""

from __future__ import annotations

from enum import Enum


class ImportRunStatus(str, Enum):
    PENDING = "pending"
    MAPPING = "mapping"
    TRANSACTION_STARTED = "transaction_started"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLBACK_COMPLETED = "rollback_completed"
    CANCELLED = "cancelled"


IMPORT_RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    ImportRunStatus.PENDING.value: frozenset(
        {
            ImportRunStatus.MAPPING.value,
            ImportRunStatus.FAILED.value,
            ImportRunStatus.CANCELLED.value,
        }
    ),
    ImportRunStatus.MAPPING.value: frozenset(
        {
            ImportRunStatus.TRANSACTION_STARTED.value,
            ImportRunStatus.FAILED.value,
            ImportRunStatus.CANCELLED.value,
        }
    ),
    ImportRunStatus.TRANSACTION_STARTED.value: frozenset(
        {
            ImportRunStatus.COMMITTING.value,
            ImportRunStatus.FAILED.value,
            ImportRunStatus.ROLLING_BACK.value,
            ImportRunStatus.CANCELLED.value,
        }
    ),
    ImportRunStatus.COMMITTING.value: frozenset(
        {
            ImportRunStatus.COMPLETED.value,
            ImportRunStatus.FAILED.value,
            ImportRunStatus.ROLLING_BACK.value,
        }
    ),
    ImportRunStatus.COMPLETED.value: frozenset(
        {
            ImportRunStatus.ROLLING_BACK.value,
        }
    ),
    ImportRunStatus.FAILED.value: frozenset(
        {
            ImportRunStatus.PENDING.value,  # retry
            ImportRunStatus.ROLLING_BACK.value,
            ImportRunStatus.CANCELLED.value,
        }
    ),
    ImportRunStatus.ROLLING_BACK.value: frozenset(
        {
            ImportRunStatus.ROLLBACK_COMPLETED.value,
            ImportRunStatus.FAILED.value,
        }
    ),
    ImportRunStatus.ROLLBACK_COMPLETED.value: frozenset(),
    ImportRunStatus.CANCELLED.value: frozenset(),
}


class ImportArtifactAction(str, Enum):
    CREATED = "created"
    LINKED = "linked"
    UPDATED = "updated"


class ImportArtifactKind(str, Enum):
    INVOICE = "invoice"
    QUOTE = "quote"
    CREDIT_NOTE = "credit_note"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    CONTRACT = "contract"
    CONTACT = "contact"
    BANK_ACCOUNT = "bank_account"
    BANK_TRANSACTION = "bank_transaction"
    ACCOUNTING_ENTRY = "accounting_entry"
    GENERIC = "generic"


class RollbackReason(str, Enum):
    SQL_ERROR = "sql_error"
    TIMEOUT = "timeout"
    BUSINESS_ERROR = "business_error"
    CANCELLATION = "cancellation"
    MANUAL = "manual"
    AUTOMATIC = "automatic"
