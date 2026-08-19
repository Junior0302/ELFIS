"""Repository validation métier."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.document_processing.validation.models import (
    ElfisDocumentBusinessValidation,
    ElfisDocumentValidationIssue,
)
from app.document_processing.validation.types import BusinessValidationStatus


class BusinessValidationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, validation_id: str) -> ElfisDocumentBusinessValidation | None:
        return self._db.get(ElfisDocumentBusinessValidation, validation_id)

    def list_results(
        self,
        *,
        organization_id: int | None,
        document_id: str | None = None,
        version_id: str | None = None,
        extraction_result_id: str | None = None,
        status: str | None = None,
        requires_review: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisDocumentBusinessValidation], int]:
        q = self._db.query(ElfisDocumentBusinessValidation)
        if not platform:
            if organization_id is None:
                return [], 0
            q = q.filter(ElfisDocumentBusinessValidation.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisDocumentBusinessValidation.organization_id == organization_id)
        if document_id:
            q = q.filter(ElfisDocumentBusinessValidation.document_id == document_id)
        if version_id:
            q = q.filter(ElfisDocumentBusinessValidation.document_version_id == version_id)
        if extraction_result_id:
            q = q.filter(ElfisDocumentBusinessValidation.extraction_result_id == extraction_result_id)
        if status:
            q = q.filter(ElfisDocumentBusinessValidation.status == status)
        if requires_review is not None:
            q = q.filter(ElfisDocumentBusinessValidation.requires_review == requires_review)
        total = q.count()
        items = (
            q.order_by(
                ElfisDocumentBusinessValidation.created_at.desc(),
                ElfisDocumentBusinessValidation.id.desc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def list_issues(self, validation_id: str) -> list[ElfisDocumentValidationIssue]:
        return (
            self._db.query(ElfisDocumentValidationIssue)
            .filter(ElfisDocumentValidationIssue.business_validation_id == validation_id)
            .order_by(ElfisDocumentValidationIssue.created_at.asc())
            .all()
        )

    def get_issue(self, issue_id: str) -> ElfisDocumentValidationIssue | None:
        return self._db.get(ElfisDocumentValidationIssue, issue_id)

    def list_for_document(self, document_id: str) -> list[ElfisDocumentBusinessValidation]:
        return (
            self._db.query(ElfisDocumentBusinessValidation)
            .filter(ElfisDocumentBusinessValidation.document_id == document_id)
            .all()
        )

    def add_result(self, row: ElfisDocumentBusinessValidation, *, commit: bool = False):
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def add_issue(self, row: ElfisDocumentValidationIssue, *, commit: bool = False):
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
        return row

    def supersede_active(self, *, document_version_id: str, extraction_result_id: str, except_id: str | None = None) -> int:
        q = self._db.query(ElfisDocumentBusinessValidation).filter(
            ElfisDocumentBusinessValidation.document_version_id == document_version_id,
            ElfisDocumentBusinessValidation.extraction_result_id == extraction_result_id,
            ElfisDocumentBusinessValidation.status.in_(
                [
                    BusinessValidationStatus.VALID.value,
                    BusinessValidationStatus.VALID_WITH_WARNINGS.value,
                    BusinessValidationStatus.INVALID.value,
                    BusinessValidationStatus.REVIEW_REQUIRED.value,
                    BusinessValidationStatus.PROCESSING.value,
                    BusinessValidationStatus.PENDING.value,
                ]
            ),
        )
        if except_id:
            q = q.filter(ElfisDocumentBusinessValidation.id != except_id)
        n = 0
        for row in q.all():
            row.status = BusinessValidationStatus.SUPERSEDED.value
            n += 1
        return n
