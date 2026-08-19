"""Provider noop — aucun contenu fichier lu."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.document_processing.ocr.provider import (
    OCRPagePayload,
    OCRProviderCapabilities,
    OCRProviderResult,
    OCRRequest,
)
from app.document_processing.ocr.types import ExtractionMethod, PROVIDER_NOOP


class NoopOCRProvider:
    provider_key = PROVIDER_NOOP
    provider_version = "1.0.0"
    capabilities = OCRProviderCapabilities(
        pdf=True,
        images=True,
        multipage=True,
        native_text=False,
        confidence=True,
    )
    supported_mime_types = (
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
    )
    supported_languages = ("fra", "eng")
    max_pages = 50
    max_file_size_bytes = 20_971_520

    async def recognize(self, request: OCRRequest) -> OCRProviderResult:
        started = time.perf_counter()
        mode = (request.noop_mode or (request.options or {}).get("noop_mode") or "ok").strip().lower()
        await asyncio.sleep(0)
        duration = int((time.perf_counter() - started) * 1000)

        if mode == "retryable":
            return OCRProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                extraction_method=ExtractionMethod.NOOP.value,
                retryable=True,
                error_code="noop_retryable",
                error_message_sanitized="Échec noop retryable",
                processing_duration_ms=duration,
            )
        if mode == "permanent":
            return OCRProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                extraction_method=ExtractionMethod.NOOP.value,
                retryable=False,
                error_code="noop_permanent",
                error_message_sanitized="Échec noop permanent",
                processing_duration_ms=duration,
            )
        if mode == "timeout":
            return OCRProviderResult(
                success=False,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                extraction_method=ExtractionMethod.NOOP.value,
                retryable=True,
                error_code="timeout",
                error_message_sanitized="Timeout noop simulé",
                processing_duration_ms=duration,
            )
        if mode == "low_confidence":
            pages = [
                OCRPagePayload(page_number=1, text="[noop]", confidence=0.2),
            ]
            return OCRProviderResult(
                success=True,
                provider_key=self.provider_key,
                provider_version=self.provider_version,
                extraction_method=ExtractionMethod.NOOP.value,
                pages=pages,
                warnings=["low_confidence"],
                processing_duration_ms=duration,
            )

        n_pages = int((request.options or {}).get("noop_pages") or 1)
        n_pages = max(1, min(n_pages, request.max_pages))
        pages = [
            OCRPagePayload(
                page_number=i,
                text=f"[noop page {i}]",
                confidence=0.99,
                detected_language="und",
            )
            for i in range(1, n_pages + 1)
        ]
        return OCRProviderResult(
            success=True,
            provider_key=self.provider_key,
            provider_version=self.provider_version,
            extraction_method=ExtractionMethod.NOOP.value,
            pages=pages,
            detected_languages=["und"],
            warnings=["noop_provider_no_real_ocr"],
            processing_duration_ms=duration,
        )

    def health(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "available": True,
            "real_ocr": False,
            "summary": "noop — aucun OCR réel",
        }
