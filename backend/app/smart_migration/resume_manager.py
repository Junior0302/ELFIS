"""ResumeManager — reprise après crash / timeout / arrêt."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.smart_migration.enums import (
    BatchItemStatus,
    BatchStatus,
    SmartRunStatus,
    TERMINAL_ITEM,
)
from app.smart_migration.exceptions import SmartStateError
from app.smart_migration.models import (
    ElfisSmartMigrationBatch,
    ElfisSmartMigrationBatchItem,
    ElfisSmartMigrationRun,
)


class ResumeManager:
    def __init__(self, db: Session):
        self._db = db

    def find_incomplete_items(
        self, smart_run_id: str
    ) -> list[ElfisSmartMigrationBatchItem]:
        return (
            self._db.query(ElfisSmartMigrationBatchItem)
            .filter(ElfisSmartMigrationBatchItem.smart_run_id == smart_run_id)
            .filter(
                ~ElfisSmartMigrationBatchItem.status.in_(
                    [
                        BatchItemStatus.COMPLETED.value,
                        BatchItemStatus.SKIPPED.value,
                        BatchItemStatus.CANCELLED.value,
                    ]
                )
            )
            .order_by(ElfisSmartMigrationBatchItem.created_at.asc())
            .all()
        )

    def prepare_resume(self, run: ElfisSmartMigrationRun) -> ElfisSmartMigrationRun:
        if run.status == SmartRunStatus.COMPLETED.value:
            raise SmartStateError("Migration déjà terminée — rien à reprendre")
        if run.status == SmartRunStatus.CANCELLED.value:
            raise SmartStateError("Migration annulée — reprise impossible")

        # Remettre les items « running » abandonnés en pending (crash mid-flight)
        stuck = (
            self._db.query(ElfisSmartMigrationBatchItem)
            .filter(ElfisSmartMigrationBatchItem.smart_run_id == run.id)
            .filter(ElfisSmartMigrationBatchItem.status == BatchItemStatus.RUNNING.value)
            .all()
        )
        for item in stuck:
            item.status = BatchItemStatus.PENDING.value
            item.error_message = "reprise_apres_interruption"
            self._db.add(item)

        batches = (
            self._db.query(ElfisSmartMigrationBatch)
            .filter(ElfisSmartMigrationBatch.smart_run_id == run.id)
            .filter(
                ElfisSmartMigrationBatch.status.in_(
                    [
                        BatchStatus.RUNNING.value,
                        BatchStatus.PARTIAL.value,
                        BatchStatus.FAILED.value,
                        BatchStatus.PENDING.value,
                    ]
                )
            )
            .all()
        )
        for b in batches:
            if b.status == BatchStatus.RUNNING.value:
                b.status = BatchStatus.PENDING.value
            self._db.add(b)

        run.status = SmartRunStatus.RESUMING.value
        run.active_workers = 0
        run.active_batches = 0
        run.last_heartbeat_at = datetime.utcnow()
        self._db.add(run)
        self._db.flush()
        return run

    def resume(
        self,
        run: ElfisSmartMigrationRun,
        *,
        execute_batch: Callable[[ElfisSmartMigrationBatch], Any],
    ) -> ElfisSmartMigrationRun:
        self.prepare_resume(run)
        run.status = SmartRunStatus.RUNNING.value
        self._db.add(run)
        self._db.flush()

        batches = (
            self._db.query(ElfisSmartMigrationBatch)
            .filter(ElfisSmartMigrationBatch.smart_run_id == run.id)
            .order_by(ElfisSmartMigrationBatch.batch_index.asc())
            .all()
        )
        for batch in batches:
            if batch.status in {
                BatchStatus.COMPLETED.value,
                BatchStatus.CANCELLED.value,
            }:
                continue
            incomplete = (
                self._db.query(ElfisSmartMigrationBatchItem)
                .filter(ElfisSmartMigrationBatchItem.batch_id == batch.id)
                .filter(
                    ~ElfisSmartMigrationBatchItem.status.in_(list(TERMINAL_ITEM))
                )
                .count()
            )
            if incomplete == 0:
                batch.status = BatchStatus.COMPLETED.value
                batch.completed_at = batch.completed_at or datetime.utcnow()
                self._db.add(batch)
                continue
            execute_batch(batch)

        return run
