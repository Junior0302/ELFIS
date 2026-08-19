"""Repository Import Engine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.import_engine.models import (
    ElfisImportArtifact,
    ElfisImportReport,
    ElfisImportRun,
)


class ImportRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_run(
        self, *, organization_id: int, import_id: str
    ) -> ElfisImportRun | None:
        return (
            self._db.query(ElfisImportRun)
            .filter(ElfisImportRun.id == import_id)
            .filter(ElfisImportRun.organization_id == organization_id)
            .first()
        )

    def list_runs(
        self,
        *,
        organization_id: int,
        migration_session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ElfisImportRun], int]:
        q = self._db.query(ElfisImportRun).filter(
            ElfisImportRun.organization_id == organization_id
        )
        if migration_session_id:
            q = q.filter(ElfisImportRun.migration_session_id == migration_session_id)
        total = q.count()
        items = (
            q.order_by(ElfisImportRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def get_report(
        self, *, organization_id: int, import_id: str
    ) -> ElfisImportReport | None:
        return (
            self._db.query(ElfisImportReport)
            .filter(ElfisImportReport.organization_id == organization_id)
            .filter(ElfisImportReport.import_run_id == import_id)
            .order_by(ElfisImportReport.version.desc())
            .first()
        )

    def list_artifacts(self, *, import_run_id: str) -> list[ElfisImportArtifact]:
        return (
            self._db.query(ElfisImportArtifact)
            .filter(ElfisImportArtifact.import_run_id == import_run_id)
            .order_by(ElfisImportArtifact.created_at.asc())
            .all()
        )
