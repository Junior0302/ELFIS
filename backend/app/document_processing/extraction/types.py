"""Types extraction structurée RC2.5.4 — pas d'IA / mapping comptable."""

from __future__ import annotations

from enum import Enum

PIPELINE_EXTRACTION_V1 = "document_extraction_v1"

STEP_RESOLVE_EFFECTIVE_TYPE = "resolve_effective_document_type"
STEP_SELECT_EXTRACTION_SCHEMA = "select_extraction_schema"
STEP_SELECT_EXTRACTION_SOURCE = "select_extraction_source"
STEP_LOAD_EXTRACTION_SOURCE = "load_extraction_source"
STEP_PERFORM_EXTRACTION = "perform_structured_extraction"
STEP_VALIDATE_EXTRACTION = "validate_extraction_schema"
STEP_PERSIST_EXTRACTION_ARTIFACT = "persist_extraction_artifact"
STEP_FINALIZE_EXTRACTION = "finalize_extraction_result"

EXTRACTION_ARTIFACT_SCHEMA = "structured_extraction_v1"
PROVIDER_NOOP = "noop"
PROVIDER_RULES = "rules"

SCHEMA_GENERIC_V1 = "generic_document_v1"
SCHEMA_INVOICE_BASIC_V1 = "invoice_basic_v1"
SCHEMA_QUOTE_BASIC_V1 = "quote_basic_v1"
SCHEMA_RECEIPT_BASIC_V1 = "receipt_basic_v1"


class ExtractionResultStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    INVALID = "invalid"
    FAILED = "failed"
    REJECTED = "rejected"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    BLOCKED = "blocked"


class ExtractedFieldStatus(str, Enum):
    EXTRACTED = "extracted"
    MISSING = "missing"
    INVALID = "invalid"
    CORRECTED = "corrected"
    EMPTY = "empty"


class FieldType(str, Enum):
    STRING = "string"
    DATE = "date"
    DECIMAL = "decimal"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CURRENCY_CODE = "currency_code"
    PERCENTAGE = "percentage"
    ENUM = "enum"
    OBJECT = "object"
    ARRAY = "array"
