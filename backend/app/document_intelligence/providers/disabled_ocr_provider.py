"""OCR désactivé — jamais de texte simulé."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.document_intelligence.document_exceptions import DocumentOCRUnavailableError
from app.document_intelligence.document_schemas import DocumentExtractionOutput
from app.document_intelligence.providers.base import OCRProvider


class DisabledOCRProvider(OCRProvider):
    provider_name = "disabled"

    def extract_text(
        self, *, path: Path, mime_type: str, filename: str
    ) -> DocumentExtractionOutput:
        raise DocumentOCRUnavailableError("OCR non configuré (ELFIS_OCR_PROVIDER=disabled)")

    def health_check(self) -> dict[str, Any]:
        return {"provider": self.provider_name, "enabled": False, "ok": False}
