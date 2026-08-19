"""Persistance Document Intelligence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.document_intelligence.document_models import ElfisDocumentTextExtraction


class DocumentExtractionRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_by_extraction_id(self, extraction_id: str) -> ElfisDocumentTextExtraction | None:
        return (
            self._db.query(ElfisDocumentTextExtraction)
            .filter(ElfisDocumentTextExtraction.extraction_id == extraction_id)
            .first()
        )

    def find_by_idempotency(self, key: str) -> ElfisDocumentTextExtraction | None:
        if not key:
            return None
        return (
            self._db.query(ElfisDocumentTextExtraction)
            .filter(ElfisDocumentTextExtraction.idempotency_key == key)
            .order_by(ElfisDocumentTextExtraction.created_at.asc())
            .first()
        )

    def find_for_document(
        self,
        *,
        organization_id: int,
        vault_document_id: str,
        document_version: int,
    ) -> ElfisDocumentTextExtraction | None:
        return (
            self._db.query(ElfisDocumentTextExtraction)
            .filter(
                ElfisDocumentTextExtraction.organization_id == organization_id,
                ElfisDocumentTextExtraction.vault_document_id == vault_document_id,
                ElfisDocumentTextExtraction.document_version == document_version,
            )
            .first()
        )

    def save(
        self, row: ElfisDocumentTextExtraction, *, commit: bool = True
    ) -> ElfisDocumentTextExtraction:
        row.updated_at = datetime.utcnow()
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_extractions(
        self,
        *,
        organization_id: int | None = None,
        status: str | None = None,
        extractor_name: str | None = None,
        requires_ocr: bool | None = None,
        requires_review: bool | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisDocumentTextExtraction], int]:
        q = self._db.query(ElfisDocumentTextExtraction)
        if organization_id is not None:
            q = q.filter(ElfisDocumentTextExtraction.organization_id == organization_id)
        if status:
            q = q.filter(ElfisDocumentTextExtraction.status == status)
        if extractor_name:
            q = q.filter(ElfisDocumentTextExtraction.extractor_name == extractor_name)
        if requires_ocr is not None:
            q = q.filter(ElfisDocumentTextExtraction.requires_ocr == requires_ocr)
        if requires_review is not None:
            q = q.filter(ElfisDocumentTextExtraction.requires_review == requires_review)
        if date_from is not None:
            q = q.filter(ElfisDocumentTextExtraction.created_at >= date_from)
        if date_to is not None:
            q = q.filter(ElfisDocumentTextExtraction.created_at <= date_to)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisDocumentTextExtraction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total
