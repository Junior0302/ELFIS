"""Politiques validation métier."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.config import settings
from app.document_processing.validation.exceptions import (
    BusinessValidationAccessDeniedError,
    BusinessValidationValidationError,
)
from app.storage.storage_models import ElfisDocumentRecord
from app.storage.storage_types import DocumentStatus


@dataclass(frozen=True)
class ValidationLimits:
    amount_tolerance: Decimal
    percentage_tolerance: Decimal
    require_confirmed_extraction: bool
    artifact_namespace: str
    max_artifact_bytes: int

    @classmethod
    def from_settings(cls) -> ValidationLimits:
        return cls(
            amount_tolerance=Decimal(
                str(getattr(settings, "document_validation_amount_tolerance", "0.02") or "0.02")
            ),
            percentage_tolerance=Decimal(
                str(getattr(settings, "document_validation_percentage_tolerance", "0.01") or "0.01")
            ),
            require_confirmed_extraction=bool(
                getattr(settings, "document_validation_require_confirmed_extraction", True)
            ),
            artifact_namespace=(
                getattr(settings, "document_extraction_artifact_namespace", None)
                or "processing-artifacts"
            ).strip(),
            max_artifact_bytes=int(
                getattr(settings, "document_extraction_max_result_bytes", 1_048_576) or 1_048_576
            ),
        )


class BusinessValidationAccessPolicy:
    def assert_document_ok(self, document: ElfisDocumentRecord, *, for_mutate: bool = False) -> None:
        if document.status == DocumentStatus.PURGED.value:
            raise BusinessValidationAccessDeniedError("document_purged", "Document purgé")
        if document.status == DocumentStatus.DELETED.value and for_mutate:
            raise BusinessValidationAccessDeniedError("document_deleted", "Document inaccessible")

    def assert_can_validate(self, document: ElfisDocumentRecord, *, quarantined: bool) -> None:
        if quarantined:
            raise BusinessValidationValidationError("object_quarantined", "Document en quarantaine")
        if document.status in (DocumentStatus.PURGED.value, DocumentStatus.DELETED.value):
            raise BusinessValidationValidationError("document_unavailable", "Document indisponible")
