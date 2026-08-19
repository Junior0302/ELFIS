"""Repository Document Extraction."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.document_extraction.enums import ExtractionStatus
from app.document_extraction.models import (
    ElfisDocumentExtraction,
    ElfisDocumentExtractionAttempt,
)


class DocumentExtractionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, extraction_id: str) -> ElfisDocumentExtraction | None:
        return self._db.get(ElfisDocumentExtraction, extraction_id)

    def get_for_org(
        self, extraction_id: str, organization_id: int
    ) -> ElfisDocumentExtraction | None:
        row = self.get(extraction_id)
        if not row or row.organization_id != organization_id:
            return None
        return row

    def find_by_fingerprint(
        self, *, organization_id: int, input_fingerprint: str
    ) -> ElfisDocumentExtraction | None:
        # Terminé d'abord
        done = (
            self._db.query(ElfisDocumentExtraction)
            .filter(ElfisDocumentExtraction.organization_id == organization_id)
            .filter(ElfisDocumentExtraction.input_fingerprint == input_fingerprint)
            .filter(ElfisDocumentExtraction.status_scope == "active")
            .filter(
                ElfisDocumentExtraction.status.in_(
                    [
                        ExtractionStatus.COMPLETED.value,
                        ExtractionStatus.COMPLETED_WITH_WARNINGS.value,
                        ExtractionStatus.AWAITING_HUMAN_VALIDATION.value,
                    ]
                )
            )
            .order_by(ElfisDocumentExtraction.created_at.desc())
            .first()
        )
        if done:
            return done
        # En cours — pour idempotence concurrente
        return (
            self._db.query(ElfisDocumentExtraction)
            .filter(ElfisDocumentExtraction.organization_id == organization_id)
            .filter(ElfisDocumentExtraction.input_fingerprint == input_fingerprint)
            .filter(ElfisDocumentExtraction.status_scope == "active")
            .filter(
                ElfisDocumentExtraction.status.in_(
                    [
                        ExtractionStatus.PENDING.value,
                        ExtractionStatus.QUEUED.value,
                        ExtractionStatus.PREPARING.value,
                        ExtractionStatus.EXTRACTING.value,
                        ExtractionStatus.NORMALIZING.value,
                        ExtractionStatus.RECONCILING.value,
                        ExtractionStatus.VALIDATING.value,
                    ]
                )
            )
            .order_by(ElfisDocumentExtraction.created_at.asc())
            .first()
        )

    def list_for_item(
        self, *, organization_id: int, document_intake_item_id: str
    ) -> list[ElfisDocumentExtraction]:
        return (
            self._db.query(ElfisDocumentExtraction)
            .filter(ElfisDocumentExtraction.organization_id == organization_id)
            .filter(ElfisDocumentExtraction.document_intake_item_id == document_intake_item_id)
            .order_by(ElfisDocumentExtraction.created_at.desc())
            .all()
        )

    def list_for_session(
        self, *, organization_id: int, migration_session_id: str, limit: int = 100
    ) -> list[ElfisDocumentExtraction]:
        return (
            self._db.query(ElfisDocumentExtraction)
            .filter(ElfisDocumentExtraction.organization_id == organization_id)
            .filter(ElfisDocumentExtraction.migration_session_id == migration_session_id)
            .order_by(ElfisDocumentExtraction.created_at.desc())
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def add(self, row: ElfisDocumentExtraction, *, commit: bool = True) -> ElfisDocumentExtraction:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save(self, row: ElfisDocumentExtraction, *, commit: bool = True) -> ElfisDocumentExtraction:
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def add_attempt(
        self, row: ElfisDocumentExtractionAttempt, *, commit: bool = False
    ) -> ElfisDocumentExtractionAttempt:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row
