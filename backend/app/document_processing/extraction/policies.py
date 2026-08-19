"""Politiques et limites extraction."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.document_processing.extraction.exceptions import ExtractionAccessDeniedError, ExtractionValidationError
from app.storage.storage_models import ElfisDocumentRecord
from app.storage.storage_types import DocumentStatus


@dataclass(frozen=True)
class ExtractionLimits:
    max_source_characters: int
    max_result_bytes: int
    max_fields: int
    max_array_items: int
    max_field_length: int
    timeout_seconds: int
    review_threshold: float
    artifact_namespace: str

    @classmethod
    def from_settings(cls) -> ExtractionLimits:
        return cls(
            max_source_characters=int(
                getattr(settings, "document_extraction_max_source_characters", 500_000) or 500_000
            ),
            max_result_bytes=int(
                getattr(settings, "document_extraction_max_result_bytes", 1_048_576) or 1_048_576
            ),
            max_fields=int(getattr(settings, "document_extraction_max_fields", 100) or 100),
            max_array_items=int(getattr(settings, "document_extraction_max_array_items", 50) or 50),
            max_field_length=int(
                getattr(settings, "document_extraction_max_field_length", 2000) or 2000
            ),
            timeout_seconds=int(
                getattr(settings, "document_extraction_timeout_seconds", 120) or 120
            ),
            review_threshold=float(
                getattr(settings, "document_extraction_review_threshold", 0.80) or 0.80
            ),
            artifact_namespace=(
                getattr(settings, "document_extraction_artifact_namespace", None)
                or "processing-artifacts"
            ).strip(),
        )


class ExtractionAccessPolicy:
    """Accès tenant-safe aux résultats d'extraction."""

    def assert_document_readable(self, document: ElfisDocumentRecord, *, for_content: bool = False) -> None:
        if document.status == DocumentStatus.PURGED.value:
            raise ExtractionAccessDeniedError("document_purged", "Document purgé")
        if document.status == DocumentStatus.DELETED.value and for_content:
            raise ExtractionAccessDeniedError("document_deleted", "Document inaccessible")

    def assert_can_extract(self, document: ElfisDocumentRecord, *, storage_quarantined: bool) -> None:
        if storage_quarantined:
            raise ExtractionValidationError("object_quarantined", "Document en quarantaine")
        if document.status == DocumentStatus.PURGED.value:
            raise ExtractionValidationError("document_purged", "Document purgé")
        if document.status == DocumentStatus.DELETED.value:
            raise ExtractionValidationError("document_deleted", "Document soft-deleted")
