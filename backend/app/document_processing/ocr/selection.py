"""Sélection explicable du provider OCR."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.document_processing.ocr.exceptions import OCRValidationError
from app.document_processing.ocr.provider_registry import OCRProviderRegistry, get_ocr_provider_registry
from app.document_processing.ocr.types import PROVIDER_NATIVE_PDF, PROVIDER_NOOP


@dataclass
class OCRProviderSelection:
    selected_provider: str
    reason_code: str
    fallback_chain: list[str] = field(default_factory=list)
    capabilities_checked: list[str] = field(default_factory=list)
    extraction_method_hint: str | None = None


class OCRProviderSelectionService:
    def __init__(self, registry: OCRProviderRegistry | None = None) -> None:
        self._registry = registry or get_ocr_provider_registry()

    def select(
        self,
        *,
        mime_type: str,
        has_native_text_hint: bool | None = None,
        force_image_ocr: bool | None = None,
    ) -> OCRProviderSelection:
        mime = (mime_type or "").lower().strip()
        configured = (getattr(settings, "document_ocr_provider", None) or PROVIDER_NOOP).strip().lower()
        force = (
            force_image_ocr
            if force_image_ocr is not None
            else bool(getattr(settings, "document_ocr_force_image_ocr", False))
        )
        native_enabled = bool(getattr(settings, "document_ocr_native_pdf_text_enabled", True))
        allowed_raw = getattr(
            settings,
            "document_ocr_allowed_mime_types",
            "application/pdf,image/png,image/jpeg,image/tiff",
        )
        allowed = {m.strip().lower() for m in str(allowed_raw or "").split(",") if m.strip()}
        if mime and allowed and mime not in allowed:
            raise OCRValidationError("mime_not_allowed", "MIME non autorisé pour OCR")

        if configured in ("tesseract", "external"):
            raise OCRValidationError(
                "ocr_provider_unavailable",
                f"Provider {configured} non activé dans RC2.5.3",
            )

        caps: list[str] = ["config"]

        # Mode tests / défaut sûr
        if configured == PROVIDER_NOOP:
            return OCRProviderSelection(
                selected_provider=PROVIDER_NOOP,
                reason_code="configured_noop",
                fallback_chain=[PROVIDER_NOOP],
                capabilities_checked=caps,
                extraction_method_hint="noop",
            )

        if mime.startswith("image/"):
            caps.append("images")
            raise OCRValidationError(
                "image_ocr_unavailable",
                "OCR image non activé (RC2.5.3 : noop|native_pdf uniquement)",
            )

        if "pdf" in mime or mime == "application/pdf":
            caps.extend(["pdf", "native_text"])
            if force:
                raise OCRValidationError(
                    "forced_image_ocr_unavailable",
                    "Force image OCR sans provider image activé",
                )
            if configured == PROVIDER_NATIVE_PDF or (native_enabled and configured == PROVIDER_NATIVE_PDF):
                return OCRProviderSelection(
                    selected_provider=PROVIDER_NATIVE_PDF,
                    reason_code="configured_native_pdf"
                    if has_native_text_hint is not False
                    else "pdf_scanned_native_fallback",
                    fallback_chain=[PROVIDER_NATIVE_PDF],
                    capabilities_checked=caps,
                    extraction_method_hint="native_pdf_text",
                )
            if native_enabled:
                return OCRProviderSelection(
                    selected_provider=PROVIDER_NATIVE_PDF,
                    reason_code="pdf_prefer_native_text",
                    fallback_chain=[PROVIDER_NATIVE_PDF],
                    capabilities_checked=caps,
                    extraction_method_hint="native_pdf_text",
                )

        raise OCRValidationError("ocr_provider_unresolved", "Aucun provider OCR applicable")
