"""Interface OCR provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.document_intelligence.document_schemas import DocumentExtractionOutput


class OCRProvider(ABC):
    provider_name: str

    @abstractmethod
    def extract_text(
        self, *, path: Path, mime_type: str, filename: str
    ) -> DocumentExtractionOutput:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError
