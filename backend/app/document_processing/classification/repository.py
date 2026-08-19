"""Repository classifications."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.document_processing.classification.models import ElfisDocumentClassification
from app.document_processing.classification.types import ClassificationStatus


class ClassificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, classification_id: str) -> ElfisDocumentClassification | None:
        return self._db.get(ElfisDocumentClassification, classification_id)

    def find_active(
        self,
        *,
        document_version_id: str,
        classifier_key: str,
        classifier_version: str,
    ) -> ElfisDocumentClassification | None:
        return (
            self._db.query(ElfisDocumentClassification)
            .filter(
                ElfisDocumentClassification.document_version_id == document_version_id,
                ElfisDocumentClassification.classifier_key == classifier_key,
                ElfisDocumentClassification.classifier_version == classifier_version,
                ElfisDocumentClassification.status.in_(
                    [
                        ClassificationStatus.PROPOSED.value,
                        ClassificationStatus.CONFIRMED.value,
                    ]
                ),
            )
            .order_by(ElfisDocumentClassification.created_at.desc())
            .first()
        )

    def list_for_version(self, document_version_id: str) -> list[ElfisDocumentClassification]:
        return (
            self._db.query(ElfisDocumentClassification)
            .filter(ElfisDocumentClassification.document_version_id == document_version_id)
            .order_by(
                ElfisDocumentClassification.created_at.desc(),
                ElfisDocumentClassification.id.desc(),
            )
            .all()
        )

    def list_classifications(
        self,
        *,
        organization_id: int | None,
        document_id: str | None = None,
        version_id: str | None = None,
        predicted_type: str | None = None,
        confirmed_type: str | None = None,
        status: str | None = None,
        requires_review: bool | None = None,
        classifier_key: str | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisDocumentClassification], int]:
        q = self._db.query(ElfisDocumentClassification)
        if not platform:
            if organization_id is None:
                return [], 0
            q = q.filter(ElfisDocumentClassification.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisDocumentClassification.organization_id == organization_id)
        if document_id:
            q = q.filter(ElfisDocumentClassification.document_id == document_id)
        if version_id:
            q = q.filter(ElfisDocumentClassification.document_version_id == version_id)
        if predicted_type:
            q = q.filter(ElfisDocumentClassification.predicted_type == predicted_type)
        if confirmed_type:
            q = q.filter(ElfisDocumentClassification.confirmed_type == confirmed_type)
        if status:
            q = q.filter(ElfisDocumentClassification.status == status)
        if requires_review is not None:
            q = q.filter(ElfisDocumentClassification.requires_review == requires_review)
        if classifier_key:
            q = q.filter(ElfisDocumentClassification.classifier_key == classifier_key)
        total = q.count()
        items = (
            q.order_by(
                ElfisDocumentClassification.created_at.desc(),
                ElfisDocumentClassification.id.desc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def add(self, row: ElfisDocumentClassification, *, commit: bool = False) -> ElfisDocumentClassification:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def supersede_active(
        self,
        *,
        document_version_id: str,
        classifier_key: str,
        except_id: str | None = None,
    ) -> int:
        q = self._db.query(ElfisDocumentClassification).filter(
            ElfisDocumentClassification.document_version_id == document_version_id,
            ElfisDocumentClassification.classifier_key == classifier_key,
            ElfisDocumentClassification.status.in_(
                [ClassificationStatus.PROPOSED.value, ClassificationStatus.CONFIRMED.value]
            ),
        )
        if except_id:
            q = q.filter(ElfisDocumentClassification.id != except_id)
        n = 0
        for row in q.all():
            row.status = ClassificationStatus.SUPERSEDED.value
            n += 1
        return n
