"""Types OCR RC2.5.3 — framework providers, pas d'IA générative."""

from __future__ import annotations

from enum import Enum


class OCRResultStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    BLOCKED = "blocked"


class OCRPageStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    EMPTY = "empty"


class ExtractionMethod(str, Enum):
    NOOP = "noop"
    NATIVE_PDF_TEXT = "native_pdf_text"
    IMAGE_OCR = "image_ocr"
    UNKNOWN = "unknown"


PIPELINE_OCR_V1 = "document_ocr_v1"

STEP_SELECT_OCR_PROVIDER = "select_ocr_provider"
STEP_PREPARE_OCR_INPUT = "prepare_ocr_input"
STEP_PERFORM_OCR = "perform_ocr"
STEP_PERSIST_OCR_ARTIFACT = "persist_ocr_artifact"
STEP_FINALIZE_OCR_RESULT = "finalize_ocr_result"

OCR_SCHEMA_VERSION = "ocr_text_v1"
PROVIDER_NOOP = "noop"
PROVIDER_NATIVE_PDF = "native_pdf"
