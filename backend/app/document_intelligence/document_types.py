"""Types Document Intelligence."""

from __future__ import annotations


class ExtractorNames:
    PDF_TEXT = "pdf_text"
    PLAIN_TEXT = "plain_text"
    IMAGE_OCR = "image_ocr"


class ExtractionStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    REQUIRES_OCR = "requires_ocr"
    REQUIRES_REVIEW = "requires_review"
    CANCELLED = "cancelled"


ALLOWED_MIME_TYPES_V1: frozenset[str] = frozenset(
    {
        "application/pdf",
        "text/plain",
    }
)

PREPARED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)

MIME_TO_EXTRACTOR: dict[str, str] = {
    "application/pdf": ExtractorNames.PDF_TEXT,
    "text/plain": ExtractorNames.PLAIN_TEXT,
    "image/png": ExtractorNames.IMAGE_OCR,
    "image/jpeg": ExtractorNames.IMAGE_OCR,
    "image/webp": ExtractorNames.IMAGE_OCR,
}

EXTENSION_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
