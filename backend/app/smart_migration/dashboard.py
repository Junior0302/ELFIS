"""Dashboard temps réel Smart Migration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.smart_migration.enums import BatchStatus, SmartRunStatus
from app.smart_migration.metrics import SmartMigrationMetrics
from app.smart_migration.models import ElfisSmartMigrationBatch, ElfisSmartMigrationRun
from app.smart_migration.progress_engine import ProgressEngine


class SmartMigrationDashboard:
    def __init__(self, db: Session):
        self._db = db
        self._progress = ProgressEngine(db)
        self._metrics = SmartMigrationMetrics(db)

    def build(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        smart_run: ElfisSmartMigrationRun | None = None,
    ) -> dict[str, Any]:
        if smart_run is None:
            smart_run = (
                self._db.query(ElfisSmartMigrationRun)
                .filter(ElfisSmartMigrationRun.organization_id == organization_id)
                .filter(
                    ElfisSmartMigrationRun.migration_session_id == migration_session_id
                )
                .order_by(ElfisSmartMigrationRun.created_at.desc())
                .first()
            )

        snap = self._progress.compute_for_migration(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            smart_run=smart_run,
        )
        metrics = self._metrics.collect(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            smart_run=smart_run,
        )

        batches = []
        active_batches = 0
        if smart_run:
            rows = (
                self._db.query(ElfisSmartMigrationBatch)
                .filter(ElfisSmartMigrationBatch.smart_run_id == smart_run.id)
                .order_by(ElfisSmartMigrationBatch.batch_index.asc())
                .all()
            )
            for b in rows:
                if b.status == BatchStatus.RUNNING.value:
                    active_batches += 1
                batches.append(
                    {
                        "batch_id": b.id,
                        "batch_index": b.batch_index,
                        "status": b.status,
                        "documents": b.documents_count,
                        "completed": b.completed_count,
                        "failed": b.failed_count,
                        "progress_percent": b.progress_percent,
                        "started_at": b.started_at.isoformat() if b.started_at else None,
                        "completed_at": b.completed_at.isoformat()
                        if b.completed_at
                        else None,
                    }
                )

        return {
            "migration_id": migration_session_id,
            "smart_run_id": smart_run.id if smart_run else None,
            "status": smart_run.status if smart_run else "idle",
            "documents_total": snap.documents_total,
            "documents_completed": snap.documents_completed,
            "documents_pending": snap.documents_pending,
            "documents_failed": snap.documents_failed,
            "documents_imported": snap.documents_imported,
            "documents_awaiting": snap.documents_awaiting,
            "progress_percent": snap.progress_percent,
            "eta_seconds": smart_run.eta_seconds if smart_run else None,
            "throughput_per_min": metrics.get("throughput_per_min", 0),
            "avg_duration_ms": metrics.get("avg_duration_ms", 0),
            "active_batches": active_batches
            or (smart_run.active_batches if smart_run else 0),
            "active_workers": smart_run.active_workers if smart_run else 0,
            "estimated_cost": metrics.get("estimated_cost", 0),
            "actual_cost": metrics.get("actual_cost", 0),
            "batches": batches,
            "chart": {
                "labels": ["terminés", "en attente", "erreurs", "importés"],
                "values": [
                    snap.documents_completed,
                    snap.documents_pending,
                    snap.documents_failed,
                    snap.documents_imported,
                ],
            },
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "correlation_id": smart_run.correlation_id if smart_run else None,
        }
