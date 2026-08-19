"""Politiques OCR — limites et accès."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.document_processing.ocr.exceptions import OCRAccessDeniedError, OCRValidationError
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject
from app.storage.storage_types import DocumentStatus, StorageObjectStatus


@dataclass(frozen=True)
class OCRLimits:
    max_file_size_bytes: int = 20_971_520  # 20 MiB
    max_pages: int = 50
    max_text_characters: int = 500_000
    max_page_characters: int = 50_000
    max_processing_seconds: int = 180
    max_concurrent_pages: int = 2
    artifact_max_bytes: int = 2_097_152  # 2 MiB

    @classmethod
    def from_settings(cls) -> OCRLimits:
        return cls(
            max_file_size_bytes=int(
                getattr(settings, "document_ocr_max_file_size_bytes", 20_971_520) or 20_971_520
            ),
            max_pages=int(getattr(settings, "document_ocr_max_pages", 50) or 50),
            max_text_characters=int(
                getattr(settings, "document_ocr_max_text_characters", 500_000) or 500_000
            ),
            max_page_characters=int(
                getattr(settings, "document_ocr_max_page_characters", 50_000) or 50_000
            ),
            max_processing_seconds=int(
                getattr(settings, "document_ocr_max_processing_seconds", 180) or 180
            ),
            max_concurrent_pages=int(
                getattr(settings, "document_ocr_max_concurrent_pages", 2) or 2
            ),
            artifact_max_bytes=int(
                getattr(settings, "document_ocr_artifact_max_bytes", 2_097_152) or 2_097_152
            ),
        )


class OCRAccessPolicy:
    """Accès metadata / texte OCR — tenant + permissions."""

    def assert_document_readable(
        self,
        *,
        document: ElfisDocumentRecord,
        organization_id: int,
        storage_object: ElfisStorageObject | None,
        allow_quarantine: bool = False,
    ) -> None:
        if document.organization_id != organization_id:
            raise OCRAccessDeniedError("tenant_denied", "Document hors organisation")
        if document.status == DocumentStatus.PURGED.value:
            raise OCRAccessDeniedError("document_purged", "Document purgé")
        if document.status == DocumentStatus.DELETED.value:
            raise OCRAccessDeniedError("document_deleted", "Document soft-deleted")
        if storage_object is not None:
            if storage_object.status == StorageObjectStatus.QUARANTINED.value and not allow_quarantine:
                raise OCRValidationError("object_quarantined", "Document en quarantaine")
            if storage_object.status != StorageObjectStatus.AVAILABLE.value and not allow_quarantine:
                if storage_object.status == StorageObjectStatus.QUARANTINED.value:
                    raise OCRValidationError("object_quarantined", "Document en quarantaine")

    def assert_version_match(
        self, *, document: ElfisDocumentRecord, version: ElfisDocumentVersion
    ) -> None:
        if version.document_id != document.id:
            raise OCRValidationError("version_mismatch", "Version hors document")
