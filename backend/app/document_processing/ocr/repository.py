"""Repository OCR."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.document_processing.ocr.models import ElfisDocumentOCRPage, ElfisDocumentOCRResult
from app.document_processing.ocr.types import OCRResultStatus


class OCRRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, ocr_result_id: str) -> ElfisDocumentOCRResult | None:
        return self._db.get(ElfisDocumentOCRResult, ocr_result_id)

    def find_active(
        self,
        *,
        document_version_id: str,
        provider_key: str,
        provider_version: str,
    ) -> ElfisDocumentOCRResult | None:
        return (
            self._db.query(ElfisDocumentOCRResult)
            .filter(
                ElfisDocumentOCRResult.document_version_id == document_version_id,
                ElfisDocumentOCRResult.provider_key == provider_key,
                ElfisDocumentOCRResult.provider_version == provider_version,
                ElfisDocumentOCRResult.status.in_(
                    [
                        OCRResultStatus.COMPLETED.value,
                        OCRResultStatus.PARTIALLY_COMPLETED.value,
                        OCRResultStatus.PROCESSING.value,
                    ]
                ),
            )
            .order_by(ElfisDocumentOCRResult.created_at.desc())
            .first()
        )

    def list_results(
        self,
        *,
        organization_id: int | None,
        document_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        provider_key: str | None = None,
        requires_review: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisDocumentOCRResult], int]:
        q = self._db.query(ElfisDocumentOCRResult)
        if not platform:
            if organization_id is None:
                return [], 0
            q = q.filter(ElfisDocumentOCRResult.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisDocumentOCRResult.organization_id == organization_id)
        if document_id:
            q = q.filter(ElfisDocumentOCRResult.document_id == document_id)
        if version_id:
            q = q.filter(ElfisDocumentOCRResult.document_version_id == version_id)
        if status:
            q = q.filter(ElfisDocumentOCRResult.status == status)
        if provider_key:
            q = q.filter(ElfisDocumentOCRResult.provider_key == provider_key)
        if requires_review is not None:
            q = q.filter(ElfisDocumentOCRResult.requires_review == requires_review)
        total = q.count()
        items = (
            q.order_by(
                ElfisDocumentOCRResult.created_at.desc(),
                ElfisDocumentOCRResult.id.desc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def list_pages(self, ocr_result_id: str) -> list[ElfisDocumentOCRPage]:
        return (
            self._db.query(ElfisDocumentOCRPage)
            .filter(ElfisDocumentOCRPage.ocr_result_id == ocr_result_id)
            .order_by(ElfisDocumentOCRPage.page_number.asc())
            .all()
        )

    def add_result(self, row: ElfisDocumentOCRResult, *, commit: bool = False) -> ElfisDocumentOCRResult:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def add_page(self, row: ElfisDocumentOCRPage, *, commit: bool = False) -> ElfisDocumentOCRPage:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
        return row

    def list_for_document(self, document_id: str) -> list[ElfisDocumentOCRResult]:
        return (
            self._db.query(ElfisDocumentOCRResult)
            .filter(ElfisDocumentOCRResult.document_id == document_id)
            .all()
        )

    def supersede_active(
        self,
        *,
        document_version_id: str,
        provider_key: str,
        except_id: str | None = None,
    ) -> int:
        q = self._db.query(ElfisDocumentOCRResult).filter(
            ElfisDocumentOCRResult.document_version_id == document_version_id,
            ElfisDocumentOCRResult.provider_key == provider_key,
            ElfisDocumentOCRResult.status.in_(
                [
                    OCRResultStatus.COMPLETED.value,
                    OCRResultStatus.PARTIALLY_COMPLETED.value,
                    OCRResultStatus.PROCESSING.value,
                    OCRResultStatus.PENDING.value,
                ]
            ),
        )
        if except_id:
            q = q.filter(ElfisDocumentOCRResult.id != except_id)
        n = 0
        for row in q.all():
            row.status = OCRResultStatus.SUPERSEDED.value
            n += 1
        return n
