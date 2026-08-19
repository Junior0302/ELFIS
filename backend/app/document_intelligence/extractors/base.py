"""Interface extracteur."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.document_intelligence.document_schemas import DocumentExtractionOutput


class DocumentTextExtractor(ABC):
    extractor_name: str
    extractor_version: str = "v1"
    supported_mime_types: set[str]

    def can_handle(self, mime_type: str) -> bool:
        return (mime_type or "").lower() in self.supported_mime_types

    @abstractmethod
    def extract(self, *, path: Path, mime_type: str, filename: str) -> DocumentExtractionOutput:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        return {"extractor": self.extractor_name, "ok": True}
