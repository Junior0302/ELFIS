"""Enums stables — Storage & Document Registry (+ RC2.4 étape 3)."""

from __future__ import annotations

from enum import Enum


class StorageProviderName(str, Enum):
    LOCAL = "local"
    SUPABASE = "supabase"
    DISABLED = "disabled"


class StorageObjectStatus(str, Enum):
    PENDING = "pending"
    AVAILABLE = "available"
    QUARANTINED = "quarantined"
    FAILED = "failed"
    DELETED = "deleted"
    PURGE_PENDING = "purge_pending"
    PURGED = "purged"


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    AVAILABLE = "available"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PURGED = "purged"


class DocumentVersionStatus(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DELETED = "deleted"
    PURGED = "purged"
    QUARANTINED = "quarantined"


class DocumentPurgeStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    PURGED = "purged"
    BLOCKED = "blocked"


class DocumentSource(str, Enum):
    UPLOAD = "upload"
    GENERATED = "generated"
    EMAIL_ATTACHMENT = "email_attachment"
    IMPORT = "import"
    API = "api"
    SYSTEM = "system"
    RESTORE = "restore"


class DocumentRelationType(str, Enum):
    SOURCE = "source"
    ATTACHMENT = "attachment"
    GENERATED_OUTPUT = "generated_output"
    SUPPORTING_DOCUMENT = "supporting_document"
    INVOICE = "invoice"
    QUOTE = "quote"
    EXPORT = "export"


class DocumentEntityType(str, Enum):
    ORGANIZATION = "organization"
    USER = "user"
    INVOICE = "invoice"
    SALES_DOCUMENT = "sales_document"
    VAULT_DOCUMENT = "vault_document"
    JOB = "job"
    OTHER = "other"


class EncryptionStatus(str, Enum):
    NONE = "none"
    AT_REST = "at_rest"
    UNKNOWN = "unknown"


# Transitions document autorisées (from → frozenset(to))
DOCUMENT_TRANSITIONS: dict[str, frozenset[str]] = {
    DocumentStatus.DRAFT.value: frozenset(
        {DocumentStatus.AVAILABLE.value, DocumentStatus.FAILED.value, DocumentStatus.DELETED.value}
    ),
    DocumentStatus.AVAILABLE.value: frozenset(
        {
            DocumentStatus.ARCHIVED.value,
            DocumentStatus.DELETED.value,
            DocumentStatus.PROCESSING.value,
            DocumentStatus.FAILED.value,
        }
    ),
    DocumentStatus.PROCESSING.value: frozenset(
        {DocumentStatus.AVAILABLE.value, DocumentStatus.PROCESSED.value, DocumentStatus.FAILED.value}
    ),
    DocumentStatus.PROCESSED.value: frozenset(
        {DocumentStatus.AVAILABLE.value, DocumentStatus.ARCHIVED.value, DocumentStatus.DELETED.value}
    ),
    DocumentStatus.FAILED.value: frozenset(
        {DocumentStatus.AVAILABLE.value, DocumentStatus.DELETED.value}
    ),
    DocumentStatus.ARCHIVED.value: frozenset(
        {DocumentStatus.AVAILABLE.value, DocumentStatus.DELETED.value}
    ),
    DocumentStatus.DELETED.value: frozenset(
        {DocumentStatus.AVAILABLE.value, DocumentStatus.ARCHIVED.value, DocumentStatus.PURGED.value}
    ),
    DocumentStatus.PURGED.value: frozenset(),
}

# Liens métier qui bloquent la purge physique
PURGE_BLOCKING_RELATIONS = frozenset(
    {
        DocumentRelationType.INVOICE.value,
        DocumentRelationType.QUOTE.value,
        DocumentRelationType.SOURCE.value,
        DocumentRelationType.ATTACHMENT.value,
        DocumentRelationType.SUPPORTING_DOCUMENT.value,
    }
)
