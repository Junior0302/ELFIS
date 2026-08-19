"""Extracteur image OCR — préparé, délègue au OCRProvider."""

from __future__ import annotations

from pathlib import Path

from app.document_intelligence.document_exceptions import DocumentOCRUnavailableError
from app.document_intelligence.document_schemas import DocumentExtractionOutput
from app.document_intelligence.document_types import ExtractorNames
from app.document_intelligence.extractors.base import DocumentTextExtractor
from app.document_intelligence.providers.base import OCRProvider


class ImageOCRExtractor(DocumentTextExtractor):
    extractor_name = ExtractorNames.IMAGE_OCR
    extractor_version = "ocr-v1"
    supported_mime_types = {"image/png", "image/jpeg", "image/webp"}

    def __init__(self, ocr_provider: OCRProvider | None = None):
        self._ocr = ocr_provider

    def extract(self, *, path: Path, mime_type: str, filename: str) -> DocumentExtractionOutput:
        if self._ocr is None:
            raise DocumentOCRUnavailableError()
        return self._ocr.extract_text(path=path, mime_type=mime_type, filename=filename)
