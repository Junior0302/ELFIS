"""Enums Document Intake — lifecycle complet + sessions upload."""

from __future__ import annotations

from enum import Enum


class DocumentLifecycleStatus(str, Enum):
    """Contrat complet — ACTIVE_LIFECYCLE_STATUSES couvre Sprint 2.5 + 3."""

    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    QUARANTINED = "quarantined"
    DUPLICATE = "duplicate"
    READY_FOR_ANALYSIS = "ready_for_analysis"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYZING = "analyzing"
    OCR_PENDING = "ocr_pending"
    OCR_PROCESSING = "ocr_processing"
    OCR_COMPLETED = "ocr_completed"
    CLASSIFICATION_PENDING = "classification_pending"
    CLASSIFYING = "classifying"
    CLASSIFIED = "classified"
    READY_FOR_AI = "ready_for_ai"
    EXTRACTION_PENDING = "extraction_pending"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    AWAITING_VALIDATION = "awaiting_validation"
    HUMAN_VALIDATING = "human_validating"  # Sprint 5 — validation humaine en cours
    VALIDATED_BY_USER = "validated_by_user"
    READY_FOR_IMPORT = "ready_for_import"  # Sprint 5 — prêt, sans import exécuté
    IMPORT_PENDING = "import_pending"
    IMPORTING = "importing"
    IMPORT_COMPLETED = "import_completed"  # Sprint 6
    IMPORTED = "imported"  # alias historique → import_completed
    IMPORT_FAILED = "import_failed"
    ROLLBACK_COMPLETED = "rollback_completed"
    IMPORT_CANCELLED = "import_cancelled"
    ARCHIVE_PENDING = "archive_pending"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Alias rétrocompat Sprint 2
IntakeItemStatus = DocumentLifecycleStatus

ACTIVE_LIFECYCLE_STATUSES = frozenset(
    {
        DocumentLifecycleStatus.UPLOADED.value,
        DocumentLifecycleStatus.VALIDATING.value,
        DocumentLifecycleStatus.VALIDATED.value,
        DocumentLifecycleStatus.QUARANTINED.value,
        DocumentLifecycleStatus.DUPLICATE.value,
        DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
        DocumentLifecycleStatus.ANALYSIS_PENDING.value,
        DocumentLifecycleStatus.ANALYZING.value,
        DocumentLifecycleStatus.CLASSIFIED.value,
        DocumentLifecycleStatus.READY_FOR_AI.value,
        DocumentLifecycleStatus.OCR_PENDING.value,
        DocumentLifecycleStatus.EXTRACTION_PENDING.value,
        DocumentLifecycleStatus.EXTRACTING.value,
        DocumentLifecycleStatus.EXTRACTED.value,
        DocumentLifecycleStatus.AWAITING_VALIDATION.value,
        DocumentLifecycleStatus.HUMAN_VALIDATING.value,
        DocumentLifecycleStatus.VALIDATED_BY_USER.value,
        DocumentLifecycleStatus.READY_FOR_IMPORT.value,
        DocumentLifecycleStatus.IMPORT_PENDING.value,
        DocumentLifecycleStatus.IMPORTING.value,
        DocumentLifecycleStatus.IMPORT_COMPLETED.value,
        DocumentLifecycleStatus.IMPORTED.value,
        DocumentLifecycleStatus.IMPORT_FAILED.value,
        DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
        DocumentLifecycleStatus.IMPORT_CANCELLED.value,
        DocumentLifecycleStatus.REJECTED.value,
        DocumentLifecycleStatus.FAILED.value,
        DocumentLifecycleStatus.CANCELLED.value,
    }
)

# Transitions actives Sprint 2.5 + 3 + 4
LIFECYCLE_TRANSITIONS: dict[str, frozenset[str]] = {
    DocumentLifecycleStatus.UPLOADED.value: frozenset(
        {DocumentLifecycleStatus.VALIDATING.value}
    ),
    DocumentLifecycleStatus.VALIDATING.value: frozenset(
        {
            DocumentLifecycleStatus.VALIDATED.value,
            DocumentLifecycleStatus.QUARANTINED.value,
            DocumentLifecycleStatus.DUPLICATE.value,
            DocumentLifecycleStatus.REJECTED.value,
            DocumentLifecycleStatus.FAILED.value,
        }
    ),
    DocumentLifecycleStatus.VALIDATED.value: frozenset(
        {
            DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.DUPLICATE.value: frozenset(
        {
            DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.QUARANTINED.value: frozenset(
        {DocumentLifecycleStatus.CANCELLED.value}
    ),
    DocumentLifecycleStatus.READY_FOR_ANALYSIS.value: frozenset(
        {
            DocumentLifecycleStatus.ANALYSIS_PENDING.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.ANALYSIS_PENDING.value: frozenset(
        {
            DocumentLifecycleStatus.ANALYZING.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.ANALYZING.value: frozenset(
        {
            DocumentLifecycleStatus.CLASSIFIED.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.CLASSIFIED.value: frozenset(
        {
            DocumentLifecycleStatus.READY_FOR_AI.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.READY_FOR_AI.value: frozenset(
        {
            DocumentLifecycleStatus.EXTRACTION_PENDING.value,
            DocumentLifecycleStatus.OCR_PENDING.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.OCR_PENDING.value: frozenset(
        {
            DocumentLifecycleStatus.EXTRACTION_PENDING.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.EXTRACTION_PENDING.value: frozenset(
        {
            DocumentLifecycleStatus.EXTRACTING.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.EXTRACTING.value: frozenset(
        {
            DocumentLifecycleStatus.EXTRACTED.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.EXTRACTED.value: frozenset(
        {
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,
            DocumentLifecycleStatus.FAILED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.AWAITING_VALIDATION.value: frozenset(
        {
            DocumentLifecycleStatus.HUMAN_VALIDATING.value,
            DocumentLifecycleStatus.REJECTED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.HUMAN_VALIDATING.value: frozenset(
        {
            DocumentLifecycleStatus.VALIDATED_BY_USER.value,
            DocumentLifecycleStatus.REJECTED.value,
            DocumentLifecycleStatus.CANCELLED.value,
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,  # réouverture
        }
    ),
    DocumentLifecycleStatus.VALIDATED_BY_USER.value: frozenset(
        {
            DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            DocumentLifecycleStatus.HUMAN_VALIDATING.value,  # reprise édition
            DocumentLifecycleStatus.REJECTED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.READY_FOR_IMPORT.value: frozenset(
        {
            DocumentLifecycleStatus.IMPORT_PENDING.value,
            DocumentLifecycleStatus.HUMAN_VALIDATING.value,  # réouverture avant import
            DocumentLifecycleStatus.IMPORT_CANCELLED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.IMPORT_PENDING.value: frozenset(
        {
            DocumentLifecycleStatus.IMPORTING.value,
            DocumentLifecycleStatus.IMPORT_FAILED.value,
            DocumentLifecycleStatus.IMPORT_CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.IMPORTING.value: frozenset(
        {
            DocumentLifecycleStatus.IMPORT_COMPLETED.value,
            DocumentLifecycleStatus.IMPORTED.value,
            DocumentLifecycleStatus.IMPORT_FAILED.value,
            DocumentLifecycleStatus.IMPORT_CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.IMPORT_COMPLETED.value: frozenset(
        {
            DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
            DocumentLifecycleStatus.ARCHIVE_PENDING.value,
        }
    ),
    DocumentLifecycleStatus.IMPORTED.value: frozenset(
        {
            DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
            DocumentLifecycleStatus.ARCHIVE_PENDING.value,
        }
    ),
    DocumentLifecycleStatus.IMPORT_FAILED.value: frozenset(
        {
            DocumentLifecycleStatus.IMPORT_PENDING.value,  # retry
            DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
            DocumentLifecycleStatus.IMPORT_CANCELLED.value,
            DocumentLifecycleStatus.READY_FOR_IMPORT.value,
        }
    ),
    DocumentLifecycleStatus.ROLLBACK_COMPLETED.value: frozenset(
        {
            DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            DocumentLifecycleStatus.IMPORT_PENDING.value,  # re-import
            DocumentLifecycleStatus.IMPORT_CANCELLED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        }
    ),
    DocumentLifecycleStatus.IMPORT_CANCELLED.value: frozenset(),
    DocumentLifecycleStatus.REJECTED.value: frozenset(),
    DocumentLifecycleStatus.FAILED.value: frozenset(),
    DocumentLifecycleStatus.CANCELLED.value: frozenset(),
}


class IntakeOrigin(str, Enum):
    MIGRATION = "migration"
    MANUAL = "manual"
    API = "api"
    FOLDER = "folder"
    ZIP_MEMBER = "zip_member"


class DuplicateType(str, Enum):
    NONE = "none"
    EXACT = "exact"
    POTENTIAL = "potential"


class UploadSessionStatus(str, Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    PAUSED = "paused"
    VALIDATING = "validating"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


UPLOAD_SESSION_TRANSITIONS: dict[str, frozenset[str]] = {
    UploadSessionStatus.CREATED.value: frozenset(
        {
            UploadSessionStatus.UPLOADING.value,
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.EXPIRED.value,
        }
    ),
    UploadSessionStatus.UPLOADING.value: frozenset(
        {
            UploadSessionStatus.PAUSED.value,
            UploadSessionStatus.VALIDATING.value,
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.EXPIRED.value,
            UploadSessionStatus.PARTIALLY_COMPLETED.value,
            UploadSessionStatus.COMPLETED.value,
        }
    ),
    UploadSessionStatus.PAUSED.value: frozenset(
        {
            UploadSessionStatus.UPLOADING.value,
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.EXPIRED.value,
        }
    ),
    UploadSessionStatus.VALIDATING.value: frozenset(
        {
            UploadSessionStatus.COMPLETED.value,
            UploadSessionStatus.PARTIALLY_COMPLETED.value,
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.FAILED.value,
        }
    ),
    UploadSessionStatus.COMPLETED.value: frozenset(),
    UploadSessionStatus.PARTIALLY_COMPLETED.value: frozenset(),
    UploadSessionStatus.FAILED.value: frozenset(),
    UploadSessionStatus.CANCELLED.value: frozenset(),
    UploadSessionStatus.EXPIRED.value: frozenset(),
}


class LifecycleActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    WORKER = "worker"
    ADMIN = "admin"
    SCANNER = "scanner"


# Quotas soft (configurables plus tard via settings)
DEFAULT_MAX_FILE_BYTES = 15 * 1024 * 1024
DEFAULT_MAX_FILES_PER_BATCH = 100
DEFAULT_MAX_FILES_PER_SESSION = 500
DEFAULT_MAX_BYTES_PER_ORG = 500 * 1024 * 1024
DEFAULT_MAX_BYTES_PER_USER_BATCH = 100 * 1024 * 1024
DEFAULT_MAX_FILES_PER_UPLOAD_SESSION = 200
DEFAULT_MAX_BYTES_PER_UPLOAD_SESSION = 200 * 1024 * 1024
DEFAULT_MAX_ACTIVE_UPLOAD_SESSIONS = 20
FINGERPRINT_BLOCK_SIZE = 65536
ZIP_MAX_ENTRIES = 10_000
