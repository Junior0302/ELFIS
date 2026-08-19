"""Registre des providers OCR."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.document_processing.ocr.exceptions import OCRValidationError
from app.document_processing.ocr.provider import OCRProvider
from app.document_processing.ocr.providers.native_pdf_text import NativePdfTextProvider
from app.document_processing.ocr.providers.noop import NoopOCRProvider
from app.document_processing.ocr.types import PROVIDER_NATIVE_PDF, PROVIDER_NOOP


class OCRProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, OCRProvider] = {}
        self.register(NoopOCRProvider())
        self.register(NativePdfTextProvider())

    def register(self, provider: OCRProvider) -> None:
        self._providers[provider.provider_key] = provider

    def get(self, key: str) -> OCRProvider:
        provider = self._providers.get(key)
        if not provider:
            raise OCRValidationError("ocr_provider_unknown", f"Provider OCR inconnu: {key}")
        return provider

    def configured_key(self) -> str:
        raw = (getattr(settings, "document_ocr_provider", None) or PROVIDER_NOOP).strip().lower()
        if raw in ("tesseract", "external"):
            # préparés mais non activés sans implémentation
            raise OCRValidationError(
                "ocr_provider_unavailable",
                f"Provider {raw} non activé dans RC2.5.3",
            )
        if raw not in self._providers:
            raise OCRValidationError("ocr_provider_unknown", f"Provider OCR inconnu: {raw}")
        return raw

    def get_configured(self) -> OCRProvider:
        return self.get(self.configured_key())

    def list_public(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for key, p in sorted(self._providers.items()):
            health = p.health()
            items.append(
                {
                    "key": key,
                    "version": p.provider_version,
                    "available": bool(health.get("available")),
                    "real_ocr": bool(health.get("real_ocr")),
                    "capabilities": {
                        "pdf": p.capabilities.pdf,
                        "images": p.capabilities.images,
                        "multipage": p.capabilities.multipage,
                        "native_text": p.capabilities.native_text,
                        "confidence": p.capabilities.confidence,
                    },
                    "supported_mime_types": list(p.supported_mime_types),
                    "supported_languages": list(p.supported_languages),
                    "max_pages": p.max_pages,
                    "max_file_size_bytes": p.max_file_size_bytes,
                    "summary": health.get("summary") or health.get("library"),
                }
            )
        return items


_REGISTRY: OCRProviderRegistry | None = None


def get_ocr_provider_registry() -> OCRProviderRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = OCRProviderRegistry()
    return _REGISTRY


def reset_ocr_provider_registry_for_tests() -> None:
    global _REGISTRY
    _REGISTRY = None
