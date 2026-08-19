"""Repository extraction."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.document_processing.extraction.models import (
    ElfisDocumentExtractedField,
    ElfisDocumentExtractionResult,
    ElfisDocumentExtractionReview,
)
from app.document_processing.extraction.types import ExtractionResultStatus


class ExtractionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, extraction_id: str) -> ElfisDocumentExtractionResult | None:
        return self._db.get(ElfisDocumentExtractionResult, extraction_id)

    def find_active(
        self,
        *,
        document_version_id: str,
        ocr_result_id: str | None,
        schema_key: str,
        schema_version: str,
        provider_key: str,
        provider_version: str,
        idempotency_hash: str = "default",
    ) -> ElfisDocumentExtractionResult | None:
        q = self._db.query(ElfisDocumentExtractionResult).filter(
            ElfisDocumentExtractionResult.document_version_id == document_version_id,
            ElfisDocumentExtractionResult.schema_key == schema_key,
            ElfisDocumentExtractionResult.schema_version == schema_version,
            ElfisDocumentExtractionResult.provider_key == provider_key,
            ElfisDocumentExtractionResult.provider_version == provider_version,
            ElfisDocumentExtractionResult.idempotency_hash == idempotency_hash,
            ElfisDocumentExtractionResult.status.in_(
                [
                    ExtractionResultStatus.COMPLETED.value,
                    ExtractionResultStatus.PARTIALLY_COMPLETED.value,
                    ExtractionResultStatus.INVALID.value,
                    ExtractionResultStatus.CONFIRMED.value,
                    ExtractionResultStatus.PROCESSING.value,
                ]
            ),
        )
        if ocr_result_id:
            q = q.filter(ElfisDocumentExtractionResult.ocr_result_id == ocr_result_id)
        return q.order_by(ElfisDocumentExtractionResult.created_at.desc()).first()

    def list_results(
        self,
        *,
        organization_id: int | None,
        document_id: str | None = None,
        version_id: str | None = None,
        ocr_result_id: str | None = None,
        schema_key: str | None = None,
        provider_key: str | None = None,
        status: str | None = None,
        requires_review: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisDocumentExtractionResult], int]:
        q = self._db.query(ElfisDocumentExtractionResult)
        if not platform:
            if organization_id is None:
                return [], 0
            q = q.filter(ElfisDocumentExtractionResult.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisDocumentExtractionResult.organization_id == organization_id)
        if document_id:
            q = q.filter(ElfisDocumentExtractionResult.document_id == document_id)
        if version_id:
            q = q.filter(ElfisDocumentExtractionResult.document_version_id == version_id)
        if ocr_result_id:
            q = q.filter(ElfisDocumentExtractionResult.ocr_result_id == ocr_result_id)
        if schema_key:
            q = q.filter(ElfisDocumentExtractionResult.schema_key == schema_key)
        if provider_key:
            q = q.filter(ElfisDocumentExtractionResult.provider_key == provider_key)
        if status:
            q = q.filter(ElfisDocumentExtractionResult.status == status)
        if requires_review is not None:
            q = q.filter(ElfisDocumentExtractionResult.requires_review == requires_review)
        total = q.count()
        items = (
            q.order_by(
                ElfisDocumentExtractionResult.created_at.desc(),
                ElfisDocumentExtractionResult.id.desc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def list_fields(self, extraction_id: str) -> list[ElfisDocumentExtractedField]:
        return (
            self._db.query(ElfisDocumentExtractedField)
            .filter(ElfisDocumentExtractedField.extraction_result_id == extraction_id)
            .order_by(ElfisDocumentExtractedField.field_path.asc())
            .all()
        )

    def list_for_document(self, document_id: str) -> list[ElfisDocumentExtractionResult]:
        return (
            self._db.query(ElfisDocumentExtractionResult)
            .filter(ElfisDocumentExtractionResult.document_id == document_id)
            .all()
        )

    def add_result(
        self, row: ElfisDocumentExtractionResult, *, commit: bool = False
    ) -> ElfisDocumentExtractionResult:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def add_field(self, row: ElfisDocumentExtractedField, *, commit: bool = False) -> ElfisDocumentExtractedField:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
        return row

    def add_review(
        self, row: ElfisDocumentExtractionReview, *, commit: bool = False
    ) -> ElfisDocumentExtractionReview:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
        return row

    def supersede_active(
        self,
        *,
        document_version_id: str,
        schema_key: str,
        provider_key: str,
        except_id: str | None = None,
    ) -> int:
        q = self._db.query(ElfisDocumentExtractionResult).filter(
            ElfisDocumentExtractionResult.document_version_id == document_version_id,
            ElfisDocumentExtractionResult.schema_key == schema_key,
            ElfisDocumentExtractionResult.provider_key == provider_key,
            ElfisDocumentExtractionResult.status.in_(
                [
                    ExtractionResultStatus.COMPLETED.value,
                    ExtractionResultStatus.PARTIALLY_COMPLETED.value,
                    ExtractionResultStatus.INVALID.value,
                    ExtractionResultStatus.PROCESSING.value,
                    ExtractionResultStatus.PENDING.value,
                    ExtractionResultStatus.CONFIRMED.value,
                ]
            ),
        )
        if except_id:
            q = q.filter(ElfisDocumentExtractionResult.id != except_id)
        n = 0
        for row in q.all():
            row.status = ExtractionResultStatus.SUPERSEDED.value
            n += 1
        return n
