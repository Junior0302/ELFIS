"""Enums Document Extraction."""

from __future__ import annotations

from enum import Enum


class ExtractionStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PREPARING = "preparing"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    RECONCILING = "reconciling"
    VALIDATING = "validating"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    AWAITING_HUMAN_VALIDATION = "awaiting_human_validation"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    OCR_PENDING = "ocr_pending"


class ExtractionStrategy(str, Enum):
    HEURISTIC = "heuristic"
    STRUCTURED = "structured"
    LLM = "llm"
    HEURISTIC_PLUS_LLM = "heuristic_plus_llm"
    FALLBACK = "fallback"


class FieldSource(str, Enum):
    HEURISTIC = "heuristic"
    STRUCTURED_FILE = "structured_file"
    NATIVE_TEXT = "native_text"
    OCR = "ocr"
    LLM = "llm"
    DERIVED = "derived"
    USER_CORRECTED = "user_corrected"


class IneligibilityReason(str, Enum):
    DOCUMENT_NOT_READY = "DOCUMENT_NOT_READY"
    DOCUMENT_QUARANTINED = "DOCUMENT_QUARANTINED"
    DOCUMENT_REJECTED = "DOCUMENT_REJECTED"
    DOCUMENT_CANCELLED = "DOCUMENT_CANCELLED"
    ANALYSIS_MISSING = "ANALYSIS_MISSING"
    UNSUPPORTED_DOCUMENT_TYPE = "UNSUPPORTED_DOCUMENT_TYPE"
    EXTRACTION_ALREADY_RUNNING = "EXTRACTION_ALREADY_RUNNING"
    ORGANIZATION_MISMATCH = "ORGANIZATION_MISMATCH"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    OCR_REQUIRED = "OCR_REQUIRED"
