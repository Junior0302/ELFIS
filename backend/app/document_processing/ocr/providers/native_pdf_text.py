"""Extraction texte PDF natif via pypdf — pas d'OCR image, pas d'exécution JS."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.document_processing.ocr.exceptions import OCRPermanentError, OCRRetryableError
from app.document_processing.ocr.provider import (
    OCRPagePayload,
    OCRProviderCapabilities,
    OCRProviderResult,
    OCRRequest,
)
from app.document_processing.ocr.sanitization import sanitize_ocr_error
from app.document_processing.ocr.types import ExtractionMethod, PROVIDER_NATIVE_PDF


class NativePdfTextProvider:
    """Lit uniquement le texte sélectionnable déjà présent dans le PDF."""

    provider_key = PROVIDER_NATIVE_PDF
    provider_version = "1.0.0"
    capabilities = OCRProviderCapabilities(
        pdf=True,
        images=False,
        multipage=True,
        native_text=True,
        confidence=False,
    )
    supported_mime_types = ("application/pdf",)
    supported_languages = ()
    max_pages = 50
    max_file_size_bytes = 20_971_520

    async def recognize(self, request: OCRRequest) -> OCRProviderResult:
        started = time.perf_counter()
        if not request.temp_path or not request.temp_path.is_file():
            raise OCRPermanentError("input_missing", "Fichier temporaire absent")
        mime = (request.mime_type or "").lower()
        if mime not in self.supported_mime_types and not mime.endswith("pdf"):
            raise OCRPermanentError("mime_unsupported", "MIME non supporté pour native_pdf")

        try:
            pages = await asyncio.wait_for(
                asyncio.to_thread(
                    self._extract_sync,
                    request,
                ),
                timeout=max(5, int((request.options or {}).get("timeout_seconds") or 60)),
            )
        except asyncio.TimeoutError as exc:
            raise OCRRetryableError("timeout", "Timeout extraction PDF native") from exc
        except OCRPermanentError:
            raise
        except Exception as exc:
            raise OCRPermanentError("pdf_extract_failed", sanitize_ocr_error(str(exc))) from exc

        duration = int((time.perf_counter() - started) * 1000)
        total_chars = sum(len(p.text) for p in pages)
        partial = bool((request.options or {}).get("_partial"))
        warnings = list((request.options or {}).get("_warnings") or [])
        if total_chars == 0:
            warnings.append("no_native_text")
        return OCRProviderResult(
            success=True,
            provider_key=self.provider_key,
            provider_version=self.provider_version,
            extraction_method=ExtractionMethod.NATIVE_PDF_TEXT.value,
            pages=pages,
            detected_languages=[],
            warnings=warnings,
            processing_duration_ms=duration,
            partially_completed=partial,
        )

    def _extract_sync(self, request: OCRRequest) -> list[OCRPagePayload]:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        path = request.temp_path
        assert path is not None
        try:
            reader = PdfReader(str(path), strict=False)
        except PdfReadError as exc:
            raise OCRPermanentError("pdf_corrupt", "PDF illisible") from exc
        except Exception as exc:
            msg = sanitize_ocr_error(str(exc)).lower()
            if "encrypt" in msg or "password" in msg:
                raise OCRPermanentError("pdf_encrypted", "PDF chiffré") from exc
            raise OCRPermanentError("pdf_open_failed", "Ouverture PDF impossible") from exc

        if getattr(reader, "is_encrypted", False):
            # tentative sans mot de passe ; sinon échec
            try:
                ok = reader.decrypt("")  # type: ignore[attr-defined]
                if not ok:
                    raise OCRPermanentError("pdf_encrypted", "PDF chiffré")
            except OCRPermanentError:
                raise
            except Exception as exc:
                raise OCRPermanentError("pdf_encrypted", "PDF chiffré") from exc

        n = len(reader.pages)
        max_pages = min(n, request.max_pages)
        if n > request.max_pages:
            request.options = dict(request.options or {})
            request.options["_partial"] = True
            request.options["_warnings"] = list(request.options.get("_warnings") or []) + [
                "page_limit_reached"
            ]

        pages: list[OCRPagePayload] = []
        total = 0
        for i in range(max_pages):
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:
                text = ""
            text = text[: request.max_page_characters]
            total += len(text)
            if total > request.max_text_characters:
                text = text[: max(0, len(text) - (total - request.max_text_characters))]
                pages.append(
                    OCRPagePayload(
                        page_number=i + 1,
                        text=text,
                        warnings=["text_limit_reached"],
                    )
                )
                request.options = dict(request.options or {})
                request.options["_partial"] = True
                request.options["_warnings"] = list(request.options.get("_warnings") or []) + [
                    "text_limit_reached"
                ]
                break
            pages.append(
                OCRPagePayload(
                    page_number=i + 1,
                    text=text,
                    warnings=["empty_page"] if not text.strip() else [],
                )
            )
        return pages

    def health(self) -> dict[str, Any]:
        try:
            import pypdf  # noqa: F401

            return {
                "provider_key": self.provider_key,
                "available": True,
                "real_ocr": False,
                "native_pdf_text": True,
                "library": "pypdf",
            }
        except Exception:
            return {
                "provider_key": self.provider_key,
                "available": False,
                "real_ocr": False,
                "error_code": "pypdf_missing",
            }
