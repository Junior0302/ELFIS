"""Scheduler — orchestration séquentielle des lots."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.smart_migration.batch_manager import BatchManager
from app.smart_migration.enums import BatchStatus, SmartRunStatus
from app.smart_migration.models import ElfisSmartMigrationBatch, ElfisSmartMigrationRun


class SmartMigrationScheduler:
    def __init__(self, db: Session):
        self._db = db
        self._batches = BatchManager(db)

    def run_all_batches(
        self,
        run: ElfisSmartMigrationRun,
        *,
        process_item: Callable[[Any], dict[str, Any]],
        stop_on_cancel: Callable[[], bool] | None = None,
    ) -> ElfisSmartMigrationRun:
        run.status = SmartRunStatus.RUNNING.value
        self._db.add(run)
        self._db.flush()

        for batch in self._batches.list_batches(run.id):
            if stop_on_cancel and stop_on_cancel():
                break
            # refresh run status
            self._db.refresh(run)
            if run.status == SmartRunStatus.CANCELLED.value:
                break
            if batch.status in {
                BatchStatus.COMPLETED.value,
                BatchStatus.CANCELLED.value,
            }:
                continue
            self._batches.execute_batch(batch, run, process_item=process_item)
        return run
