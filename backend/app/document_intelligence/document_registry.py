"""Registry extracteurs Document Intelligence."""

from __future__ import annotations

from app.document_intelligence.extractors.base import DocumentTextExtractor
from app.document_intelligence.extractors.image_ocr_extractor import ImageOCRExtractor
from app.document_intelligence.extractors.pdf_text_extractor import PdfTextExtractor
from app.document_intelligence.extractors.plain_text_extractor import PlainTextExtractor
from app.document_intelligence.providers.base import OCRProvider
from app.document_intelligence.providers.disabled_ocr_provider import DisabledOCRProvider


class DocumentExtractorRegistry:
    def __init__(self) -> None:
        self._by_name: dict[str, DocumentTextExtractor] = {}

    def register(self, extractor: DocumentTextExtractor) -> None:
        name = (extractor.extractor_name or "").strip()
        if not name:
            raise ValueError("extractor_name requis")
        if name in self._by_name and self._by_name[name] is not extractor:
            raise ValueError(f"Extracteur déjà enregistré: {name}")
        self._by_name[name] = extractor

    def get(self, name: str) -> DocumentTextExtractor:
        if name not in self._by_name:
            raise KeyError(name)
        return self._by_name[name]

    def for_mime(self, mime_type: str) -> DocumentTextExtractor | None:
        mime = (mime_type or "").lower()
        for extractor in self._by_name.values():
            if extractor.can_handle(mime):
                return extractor
        return None

    def clear(self) -> None:
        self._by_name.clear()


default_extractor_registry = DocumentExtractorRegistry()


def get_ocr_provider() -> OCRProvider:
    from app.config import settings

    if not settings.elfis_ocr_enabled or (settings.elfis_ocr_provider or "").lower() == "disabled":
        return DisabledOCRProvider()
    # Providers futurs (OpenAI Vision, Azure, etc.) — non branchés en V1
    return DisabledOCRProvider()


def bootstrap_extractors(registry: DocumentExtractorRegistry | None = None) -> DocumentExtractorRegistry:
    reg = registry or default_extractor_registry
    if not reg._by_name:
        reg.register(PdfTextExtractor())
        reg.register(PlainTextExtractor())
        reg.register(ImageOCRExtractor(ocr_provider=get_ocr_provider()))
    return reg
