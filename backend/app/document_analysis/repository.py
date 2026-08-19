"""Repository Document Analysis."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.document_analysis.models import ElfisDocumentAnalysisReport


class DocumentAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, report_id: str) -> ElfisDocumentAnalysisReport | None:
        return self._db.get(ElfisDocumentAnalysisReport, report_id)

    def get_for_org(
        self, report_id: str, organization_id: int
    ) -> ElfisDocumentAnalysisReport | None:
        row = self.get(report_id)
        if not row or row.organization_id != organization_id:
            return None
        return row

    def get_latest_for_item(
        self, *, organization_id: int, document_intake_item_id: str
    ) -> ElfisDocumentAnalysisReport | None:
        return (
            self._db.query(ElfisDocumentAnalysisReport)
            .filter(ElfisDocumentAnalysisReport.organization_id == organization_id)
            .filter(
                ElfisDocumentAnalysisReport.document_intake_item_id
                == document_intake_item_id
            )
            .order_by(ElfisDocumentAnalysisReport.created_at.desc())
            .first()
        )

    def list_for_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ElfisDocumentAnalysisReport], int]:
        q = (
            self._db.query(ElfisDocumentAnalysisReport)
            .filter(ElfisDocumentAnalysisReport.organization_id == organization_id)
            .filter(
                ElfisDocumentAnalysisReport.migration_session_id == migration_session_id
            )
        )
        total = q.count()
        rows = (
            q.order_by(ElfisDocumentAnalysisReport.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return rows, int(total)

    def add(
        self, row: ElfisDocumentAnalysisReport, *, commit: bool = True
    ) -> ElfisDocumentAnalysisReport:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save(
        self, row: ElfisDocumentAnalysisReport, *, commit: bool = True
    ) -> ElfisDocumentAnalysisReport:
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row
