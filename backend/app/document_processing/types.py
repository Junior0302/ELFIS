"""Types Document Processing RC2.5.1 — aucun OCR/IA."""

from __future__ import annotations

from enum import Enum


class ProcessingJobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"


class ProcessingStepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"


class ProcessingAttemptStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


# Transitions job autorisées (from → to)
JOB_TRANSITIONS: dict[str, frozenset[str]] = {
    ProcessingJobStatus.PENDING.value: frozenset(
        {
            ProcessingJobStatus.QUEUED.value,
            ProcessingJobStatus.CANCELLED.value,
            ProcessingJobStatus.BLOCKED.value,
        }
    ),
    ProcessingJobStatus.QUEUED.value: frozenset(
        {
            ProcessingJobStatus.RUNNING.value,
            ProcessingJobStatus.CANCELLED.value,
            ProcessingJobStatus.BLOCKED.value,
        }
    ),
    ProcessingJobStatus.RUNNING.value: frozenset(
        {
            ProcessingJobStatus.COMPLETED.value,
            ProcessingJobStatus.PARTIALLY_COMPLETED.value,
            ProcessingJobStatus.FAILED.value,
            ProcessingJobStatus.RETRYING.value,
            ProcessingJobStatus.CANCELLED.value,
            ProcessingJobStatus.TIMED_OUT.value,
            ProcessingJobStatus.BLOCKED.value,
        }
    ),
    ProcessingJobStatus.RETRYING.value: frozenset(
        {
            ProcessingJobStatus.QUEUED.value,
            ProcessingJobStatus.RUNNING.value,
            ProcessingJobStatus.FAILED.value,
            ProcessingJobStatus.CANCELLED.value,
            ProcessingJobStatus.TIMED_OUT.value,
        }
    ),
    ProcessingJobStatus.FAILED.value: frozenset(
        {ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value}
    ),
    ProcessingJobStatus.TIMED_OUT.value: frozenset(
        {ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value}
    ),
    ProcessingJobStatus.PARTIALLY_COMPLETED.value: frozenset(
        {ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value}
    ),
    ProcessingJobStatus.COMPLETED.value: frozenset(),
    ProcessingJobStatus.CANCELLED.value: frozenset(),
    ProcessingJobStatus.BLOCKED.value: frozenset({ProcessingJobStatus.CANCELLED.value}),
}

PIPELINE_BASIC_V1 = "document_basic_v1"
PIPELINE_CLASSIFICATION_V1 = "document_classification_v1"
PIPELINE_OCR_V1 = "document_ocr_v1"
PIPELINE_EXTRACTION_V1 = "document_extraction_v1"
PIPELINE_BUSINESS_VALIDATION_V1 = "document_business_validation_v1"

STEP_VALIDATE = "validate_document_available"
STEP_INSPECT = "inspect_storage_metadata"
STEP_NOOP = "noop_processing"
STEP_FINALIZE = "finalize_processing"
STEP_CLASSIFY = "classify_document"
STEP_PERSIST_CLASSIFICATION = "persist_classification"
STEP_SELECT_OCR_PROVIDER = "select_ocr_provider"
STEP_PREPARE_OCR_INPUT = "prepare_ocr_input"
STEP_PERFORM_OCR = "perform_ocr"
STEP_PERSIST_OCR_ARTIFACT = "persist_ocr_artifact"
STEP_FINALIZE_OCR_RESULT = "finalize_ocr_result"

# Extraction RC2.5.4
STEP_RESOLVE_EFFECTIVE_TYPE = "resolve_effective_document_type"
STEP_SELECT_EXTRACTION_SCHEMA = "select_extraction_schema"
STEP_SELECT_EXTRACTION_SOURCE = "select_extraction_source"
STEP_LOAD_EXTRACTION_SOURCE = "load_extraction_source"
STEP_PERFORM_EXTRACTION = "perform_structured_extraction"
STEP_VALIDATE_EXTRACTION = "validate_extraction_schema"
STEP_PERSIST_EXTRACTION_ARTIFACT = "persist_extraction_artifact"
STEP_FINALIZE_EXTRACTION = "finalize_extraction_result"

# Business validation RC2.5.5
STEP_SELECT_EFFECTIVE_EXTRACTION = "select_effective_extraction"
STEP_LOAD_EXTRACTION_CONTENT = "load_extraction_content"
STEP_SELECT_BUSINESS_RULE_SET = "select_business_rule_set"
STEP_PERFORM_BUSINESS_VALIDATION = "perform_business_validation"
STEP_PERSIST_VALIDATION_ARTIFACT = "persist_validation_artifact"
STEP_FINALIZE_BUSINESS_VALIDATION = "finalize_business_validation"
