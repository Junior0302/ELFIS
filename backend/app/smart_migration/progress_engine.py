"""ProgressEngine — progression calculée côté serveur uniquement."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.models import ElfisDocumentIntakeItem
from app.import_engine.enums import ImportRunStatus
from app.import_engine.models import ElfisImportRun
from app.smart_migration.enums import BatchItemStatus, BatchStatus
from app.smart_migration.models import (
    ElfisSmartMigrationBatch,
    ElfisSmartMigrationBatchItem,
    ElfisSmartMigrationRun,
)
from app.validation_mapping.enums import ValidationSessionStatus
from app.validation_mapping.models import ElfisValidationSession


IMPORTED_STATUSES = frozenset(
    {
        DocumentLifecycleStatus.IMPORT_COMPLETED.value,
        DocumentLifecycleStatus.IMPORTED.value,
    }
)
FAILED_STATUSES = frozenset(
    {
        DocumentLifecycleStatus.FAILED.value,
        DocumentLifecycleStatus.IMPORT_FAILED.value,
        DocumentLifecycleStatus.REJECTED.value,
    }
)
DONE_PIPELINE = frozenset(
    {
        *IMPORTED_STATUSES,
        DocumentLifecycleStatus.ARCHIVED.value,
        DocumentLifecycleStatus.CANCELLED.value,
        *FAILED_STATUSES,
    }
)


@dataclass
class ProgressSnapshot:
    documents_total: int = 0
    documents_completed: int = 0
    documents_pending: int = 0
    documents_failed: int = 0
    documents_imported: int = 0
    documents_awaiting: int = 0
    progress_percent: float = 0.0
    batch_progress: list[dict[str, Any]] | None = None
    document_progress_avg: float = 0.0
    migration_progress: float = 0.0
    global_progress: float = 0.0
    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["batch_progress"] = self.batch_progress or []
        return d


class ProgressEngine:
    def __init__(self, db: Session):
        self._db = db

    def compute_for_migration(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        smart_run: ElfisSmartMigrationRun | None = None,
    ) -> ProgressSnapshot:
        items = (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.migration_session_id == migration_session_id)
            .all()
        )
        total = len(items)
        imported = 0
        failed = 0
        completed = 0
        pending = 0
        awaiting = 0
        doc_scores: list[float] = []

        for it in items:
            st = it.lifecycle_status or it.status
            score = self._document_score(st)
            doc_scores.append(score)
            if st in IMPORTED_STATUSES:
                imported += 1
                completed += 1
            elif st in FAILED_STATUSES:
                failed += 1
                completed += 1
            elif st in DONE_PIPELINE:
                completed += 1
            elif st in {
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
                DocumentLifecycleStatus.AWAITING_VALIDATION.value,
                DocumentLifecycleStatus.HUMAN_VALIDATING.value,
            }:
                awaiting += 1
                pending += 1
            else:
                pending += 1

        avg_doc = (sum(doc_scores) / len(doc_scores)) if doc_scores else 0.0
        overall = round(avg_doc * 100.0, 2) if total else 0.0

        batch_progress: list[dict[str, Any]] = []
        if smart_run:
            batches = (
                self._db.query(ElfisSmartMigrationBatch)
                .filter(ElfisSmartMigrationBatch.smart_run_id == smart_run.id)
                .order_by(ElfisSmartMigrationBatch.batch_index.asc())
                .all()
            )
            for b in batches:
                batch_progress.append(
                    {
                        "batch_id": b.id,
                        "batch_index": b.batch_index,
                        "status": b.status,
                        "progress_percent": float(b.progress_percent or 0),
                        "documents_count": b.documents_count,
                        "completed_count": b.completed_count,
                        "failed_count": b.failed_count,
                    }
                )

        snap = ProgressSnapshot(
            documents_total=total,
            documents_completed=completed,
            documents_pending=pending,
            documents_failed=failed,
            documents_imported=imported,
            documents_awaiting=awaiting,
            progress_percent=overall,
            batch_progress=batch_progress,
            document_progress_avg=round(avg_doc * 100.0, 2),
            migration_progress=overall,
            global_progress=overall,
            computed_at=datetime.utcnow().isoformat() + "Z",
        )
        return snap

    def refresh_run(self, run: ElfisSmartMigrationRun) -> ElfisSmartMigrationRun:
        snap = self.compute_for_migration(
            organization_id=run.organization_id,
            migration_session_id=run.migration_session_id,
            smart_run=run,
        )
        run.documents_total = snap.documents_total
        run.documents_completed = snap.documents_completed
        run.documents_pending = snap.documents_pending
        run.documents_failed = snap.documents_failed
        run.documents_imported = snap.documents_imported
        run.progress_percent = snap.progress_percent
        run.last_heartbeat_at = datetime.utcnow()
        self._db.add(run)
        self._db.flush()
        return run

    def update_batch_progress(self, batch: ElfisSmartMigrationBatch) -> None:
        items = (
            self._db.query(ElfisSmartMigrationBatchItem)
            .filter(ElfisSmartMigrationBatchItem.batch_id == batch.id)
            .all()
        )
        total = len(items) or 1
        done = sum(
            1
            for i in items
            if i.status
            in {
                BatchItemStatus.COMPLETED.value,
                BatchItemStatus.SKIPPED.value,
                BatchItemStatus.CANCELLED.value,
            }
        )
        failed = sum(1 for i in items if i.status == BatchItemStatus.FAILED.value)
        batch.completed_count = done
        batch.failed_count = failed
        batch.documents_count = len(items)
        batch.progress_percent = round(100.0 * done / total, 2)
        if failed and done == len(items):
            batch.status = BatchStatus.PARTIAL.value
        elif done == len(items) and not failed:
            batch.status = BatchStatus.COMPLETED.value
            batch.completed_at = batch.completed_at or datetime.utcnow()
        self._db.add(batch)
        self._db.flush()

    @staticmethod
    def _document_score(status: str) -> float:
        """Score 0–1 selon l'avancement pipeline (réutilise statuts existants)."""
        order = [
            DocumentLifecycleStatus.UPLOADED.value,
            DocumentLifecycleStatus.VALIDATED.value,
            DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            DocumentLifecycleStatus.CLASSIFIED.value,
            DocumentLifecycleStatus.READY_FOR_AI.value,
            DocumentLifecycleStatus.EXTRACTED.value,
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,
            DocumentLifecycleStatus.HUMAN_VALIDATING.value,
            DocumentLifecycleStatus.VALIDATED_BY_USER.value,
            DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            DocumentLifecycleStatus.IMPORTING.value,
            DocumentLifecycleStatus.IMPORT_COMPLETED.value,
        ]
        if status in FAILED_STATUSES:
            return 1.0
        if status in IMPORTED_STATUSES:
            return 1.0
        try:
            idx = order.index(status)
            return (idx + 1) / len(order)
        except ValueError:
            return 0.1
