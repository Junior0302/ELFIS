"""Types validation métier documentaire RC2.5.5 — pas de validation comptable."""

from __future__ import annotations

from enum import Enum

PIPELINE_BUSINESS_VALIDATION_V1 = "document_business_validation_v1"

STEP_SELECT_EFFECTIVE_EXTRACTION = "select_effective_extraction"
STEP_LOAD_EXTRACTION_CONTENT = "load_extraction_content"
STEP_SELECT_BUSINESS_RULE_SET = "select_business_rule_set"
STEP_PERFORM_BUSINESS_VALIDATION = "perform_business_validation"
STEP_PERSIST_VALIDATION_ARTIFACT = "persist_validation_artifact"
STEP_FINALIZE_BUSINESS_VALIDATION = "finalize_business_validation"

BUSINESS_VALIDATION_ARTIFACT_SCHEMA = "business_validation_v1"

RULE_SET_INVOICE_V1 = "invoice_document_validation_v1"
RULE_SET_QUOTE_V1 = "quote_document_validation_v1"
RULE_SET_RECEIPT_V1 = "receipt_document_validation_v1"
RULE_SET_GENERIC_V1 = "generic_document_validation_v1"


class BusinessValidationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    BLOCKED = "blocked"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ResolutionType(str, Enum):
    ACCEPTED_WARNING = "accepted_warning"
    CORRECTED_EXTRACTION = "corrected_extraction"
    FALSE_POSITIVE = "false_positive"
    ACKNOWLEDGED = "acknowledged"
    REJECTED_DOCUMENT = "rejected_document"
