"""SmartMigrationOrchestrator — orchestre les pipelines existants (S2–S6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.models import ElfisDocumentIntakeItem
from app.import_engine.enums import ImportRunStatus
from app.import_engine.exceptions import ImportEngineError, ImportIdempotencyError
from app.import_engine.service import ImportEngineService
from app.smart_migration.batch_manager import BatchManager
from app.smart_migration.cleanup import CleanupManager
from app.smart_migration.dashboard import SmartMigrationDashboard
from app.smart_migration.enums import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_WORKERS,
    BatchItemStatus,
    SmartRunStatus,
)
from app.smart_migration.events import publish_smart_migration_event
from app.smart_migration.exceptions import SmartNotFoundError, SmartStateError
from app.smart_migration.metrics import SmartMigrationMetrics
from app.smart_migration.models import (
    ElfisSmartMigrationBatch,
    ElfisSmartMigrationBatchItem,
    ElfisSmartMigrationRun,
)
from app.smart_migration.progress_engine import ProgressEngine, IMPORTED_STATUSES
from app.smart_migration.reporting import SmartMigrationReporting
from app.smart_migration.resume_manager import ResumeManager
from app.smart_migration.scheduler import SmartMigrationScheduler


class SmartMigrationOrchestrator:
    """
    Couche Enterprise : batch / resume / dashboard / report.
    Ne remplace AUCUN pipeline Sprint 1–6 — délègue à ImportEngineService etc.
    """

    def __init__(self, db: Session):
        self._db = db
        self._batches = BatchManager(db)
        self._resume = ResumeManager(db)
        self._scheduler = SmartMigrationScheduler(db)
        self._progress = ProgressEngine(db)
        self._metrics = SmartMigrationMetrics(db)
        self._dashboard = SmartMigrationDashboard(db)
        self._reporting = SmartMigrationReporting(db)
        self._cleanup = CleanupManager(db)
        self._imports = ImportEngineService(db)

    def get_run(
        self, *, organization_id: int, migration_session_id: str
    ) -> ElfisSmartMigrationRun | None:
        return (
            self._db.query(ElfisSmartMigrationRun)
            .filter(ElfisSmartMigrationRun.organization_id == organization_id)
            .filter(ElfisSmartMigrationRun.migration_session_id == migration_session_id)
            .order_by(ElfisSmartMigrationRun.created_at.desc())
            .first()
        )

    def get_run_by_id(
        self, *, organization_id: int, smart_run_id: str
    ) -> ElfisSmartMigrationRun:
        run = (
            self._db.query(ElfisSmartMigrationRun)
            .filter(ElfisSmartMigrationRun.id == smart_run_id)
            .filter(ElfisSmartMigrationRun.organization_id == organization_id)
            .first()
        )
        if not run:
            raise SmartNotFoundError("Smart run introuvable")
        return run

    def status(
        self, *, organization_id: int, migration_session_id: str
    ) -> dict[str, Any]:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        snap = self._progress.compute_for_migration(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            smart_run=run,
        )
        return {
            "migration_id": migration_session_id,
            "smart_run_id": run.id if run else None,
            "status": run.status if run else "idle",
            "progress": snap.to_dict(),
            "correlation_id": run.correlation_id if run else None,
        }

    def dashboard(
        self, *, organization_id: int, migration_session_id: str
    ) -> dict[str, Any]:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        return self._dashboard.build(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            smart_run=run,
        )

    def metrics(
        self, *, organization_id: int, migration_session_id: str
    ) -> dict[str, Any]:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        return self._metrics.collect(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            smart_run=run,
        )

    def start_or_get_run(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        parallel: bool = False,
        auto_import: bool = True,
    ) -> ElfisSmartMigrationRun:
        existing = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        if existing and existing.status in {
            SmartRunStatus.RUNNING.value,
            SmartRunStatus.PENDING.value,
            SmartRunStatus.RESUMING.value,
        }:
            return existing

        docs = self._list_orchestratable_documents(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
        )
        run = ElfisSmartMigrationRun(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            status=SmartRunStatus.PENDING.value,
            batch_size=max(1, batch_size),
            max_workers=max(1, min(max_workers, 8)),
            parallel=parallel,
            documents_total=len(docs),
            correlation_id=f"sm-{uuid4().hex[:16]}",
            actor_user_id=actor_user_id,
            started_at=datetime.utcnow(),
            config_json={"auto_import": auto_import},
        )
        self._db.add(run)
        self._db.flush()
        self._batches.create_batches(run, docs, batch_size=run.batch_size)
        self._progress.refresh_run(run)
        publish_smart_migration_event(
            self._db,
            event_type="migration.started",
            run=run,
            actor_user_id=actor_user_id,
        )
        self._db.commit()
        self._db.refresh(run)
        return run

    def run_orchestration(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        parallel: bool = False,
    ) -> ElfisSmartMigrationRun:
        run = self.start_or_get_run(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            actor_user_id=actor_user_id,
            batch_size=batch_size,
            max_workers=max_workers,
            parallel=parallel,
        )
        try:
            self._scheduler.run_all_batches(
                run,
                process_item=lambda item: self._process_document_item(item, run),
                stop_on_cancel=lambda: self._is_cancelled(run.id),
            )
            self._finalize(run, actor_user_id=actor_user_id)
        except Exception as exc:  # noqa: BLE001
            run.status = SmartRunStatus.FAILED.value
            run.error_message = str(exc)[:2000]
            run.completed_at = datetime.utcnow()
            self._db.add(run)
            publish_smart_migration_event(
                self._db,
                event_type="migration.failed",
                run=run,
                actor_user_id=actor_user_id,
                metadata={"error_code": type(exc).__name__},
            )
            self._db.commit()
            raise
        return run

    def resume(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None,
    ) -> ElfisSmartMigrationRun:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        if not run:
            raise SmartNotFoundError("Aucune orchestration à reprendre")
        publish_smart_migration_event(
            self._db,
            event_type="migration.resumed",
            run=run,
            actor_user_id=actor_user_id,
        )
        self._resume.resume(
            run,
            execute_batch=lambda batch: self._batches.execute_batch(
                batch,
                run,
                process_item=lambda item: self._process_document_item(item, run),
            ),
        )
        self._finalize(run, actor_user_id=actor_user_id)
        return run

    def cancel(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None,
    ) -> ElfisSmartMigrationRun:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        if not run:
            raise SmartNotFoundError("Aucune orchestration active")
        if run.status == SmartRunStatus.COMPLETED.value:
            raise SmartStateError("Migration déjà terminée")
        run.status = SmartRunStatus.CANCELLED.value
        run.completed_at = datetime.utcnow()
        for batch in self._batches.list_batches(run.id):
            if batch.status not in {"completed", "cancelled"}:
                self._batches.cancel_batch(batch)
        self._db.add(run)
        publish_smart_migration_event(
            self._db,
            event_type="migration.cancelled",
            run=run,
            actor_user_id=actor_user_id,
        )
        self._db.commit()
        self._db.refresh(run)
        return run

    def retry_failed(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None,
    ) -> ElfisSmartMigrationRun:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        if not run:
            raise SmartNotFoundError("Aucune orchestration")
        run.status = SmartRunStatus.RUNNING.value
        self._db.add(run)
        self._db.flush()
        for batch in self._batches.list_batches(run.id):
            failed = (
                self._db.query(ElfisSmartMigrationBatchItem)
                .filter(ElfisSmartMigrationBatchItem.batch_id == batch.id)
                .filter(
                    ElfisSmartMigrationBatchItem.status == BatchItemStatus.FAILED.value
                )
                .count()
            )
            if failed:
                self._batches.restart_batch(
                    batch,
                    run,
                    process_item=lambda item: self._process_document_item(item, run),
                    failed_only=True,
                )
        self._finalize(run, actor_user_id=actor_user_id)
        return run

    def restart_batch(
        self,
        *,
        organization_id: int,
        batch_id: str,
        actor_user_id: int | None,
        failed_only: bool = False,
    ) -> ElfisSmartMigrationBatch:
        batch = self._batches.get_batch(batch_id, organization_id)
        if not batch:
            raise SmartNotFoundError("Lot introuvable")
        run = self.get_run_by_id(
            organization_id=organization_id, smart_run_id=batch.smart_run_id
        )
        return self._batches.restart_batch(
            batch,
            run,
            process_item=lambda item: self._process_document_item(item, run),
            failed_only=failed_only,
        )

    def get_report(
        self, *, organization_id: int, migration_session_id: str, fmt: str = "json"
    ) -> dict[str, Any]:
        run = self.get_run(
            organization_id=organization_id, migration_session_id=migration_session_id
        )
        if not run:
            raise SmartNotFoundError("Aucune orchestration")
        report = self._reporting.get_latest(
            organization_id=organization_id, smart_run_id=run.id
        )
        if not report:
            report = self._reporting.generate(
                run, actor_user_id=run.actor_user_id, formats=["json", "csv", "pdf"]
            )
            self._db.commit()
        out: dict[str, Any] = {
            "id": report.id,
            "version": report.version,
            "format": fmt,
            "summary": report.summary_json,
            "stats": report.stats_json,
            "created_objects": report.created_objects_json,
            "linked_objects": report.linked_objects_json,
            "errors": report.errors_json,
            "warnings": report.warnings_json,
            "duration_ms": report.duration_ms,
            "estimated_cost": report.estimated_cost,
            "actual_cost": report.actual_cost,
            "body": report.body_json,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "actor_user_id": report.actor_user_id,
        }
        if fmt == "csv":
            out["csv"] = report.body_csv
        if fmt == "pdf":
            out["pdf_base64"] = report.body_pdf
        return out

    def cleanup(
        self,
        *,
        organization_id: int,
        action: str,
        confirmed: bool = False,
        migration_session_id: str | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        return self._cleanup.execute(
            organization_id=organization_id,
            action=action,
            confirmed=confirmed,
            migration_session_id=migration_session_id,
            actor_user_id=actor_user_id,
        )

    # ── internals ──────────────────────────────────────────────

    def _list_orchestratable_documents(
        self, *, organization_id: int, migration_session_id: str
    ) -> list[dict[str, Any]]:
        items = (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.migration_session_id == migration_session_id)
            .order_by(ElfisDocumentIntakeItem.created_at.asc())
            .all()
        )
        out: list[dict[str, Any]] = []
        for it in items:
            st = it.lifecycle_status or it.status
            if st in {
                DocumentLifecycleStatus.CANCELLED.value,
                DocumentLifecycleStatus.ARCHIVED.value,
            }:
                continue
            out.append(
                {
                    "document_id": it.id,
                    "universal_document_id": it.universal_document_id,
                    "stage": st,
                    "already_done": st in IMPORTED_STATUSES,
                }
            )
        return out

    def _process_document_item(
        self, item: ElfisSmartMigrationBatchItem, run: ElfisSmartMigrationRun
    ) -> dict[str, Any]:
        """Délègue à ImportEngine si ready_for_import ; sinon skip intelligent."""
        doc = (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.id == item.document_intake_item_id)
            .filter(ElfisDocumentIntakeItem.organization_id == run.organization_id)
            .first()
        )
        if not doc:
            raise SmartNotFoundError("Document introuvable")

        st = doc.lifecycle_status or doc.status
        # Ne jamais retraiter un document déjà terminé
        if st in IMPORTED_STATUSES:
            item.status = BatchItemStatus.SKIPPED.value
            return {"stage": "import", "skipped": True, "reason": "already_imported"}

        auto_import = bool((run.config_json or {}).get("auto_import", True))
        if (
            auto_import
            and st
            in {
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
                DocumentLifecycleStatus.IMPORT_FAILED.value,
                DocumentLifecycleStatus.ROLLBACK_COMPLETED.value,
            }
        ):
            try:
                imp = self._imports.import_document(
                    organization_id=run.organization_id,
                    document_id=doc.id,
                    actor_user_id=run.actor_user_id,
                )
                publish_smart_migration_event(
                    self._db,
                    event_type="migration.progress",
                    run=run,
                    actor_user_id=run.actor_user_id,
                    metadata={
                        "document_id": doc.id,
                        "batch_id": item.batch_id,
                        "duration": imp.duration_ms,
                    },
                )
                return {
                    "stage": "import",
                    "import_id": imp.id,
                    "status": imp.status,
                    "created": len(imp.created_objects_json or []),
                    "linked": len(imp.linked_objects_json or []),
                }
            except ImportIdempotencyError:
                return {"stage": "import", "skipped": True, "reason": "idempotent"}
            except ImportEngineError as exc:
                raise SmartStateError(exc.message) from exc

        # Document pas encore ready — marque complété côté orchestration (attente pipeline)
        return {
            "stage": st,
            "awaiting_pipeline": True,
            "message": "Document hors étape import — pipelines S3–S5 non rejoués",
        }

    def _finalize(
        self, run: ElfisSmartMigrationRun, *, actor_user_id: int | None
    ) -> None:
        self._db.refresh(run)
        if run.status == SmartRunStatus.CANCELLED.value:
            self._db.commit()
            return
        self._progress.refresh_run(run)
        self._metrics.collect(
            organization_id=run.organization_id,
            migration_session_id=run.migration_session_id,
            smart_run=run,
        )
        failed_items = (
            self._db.query(ElfisSmartMigrationBatchItem)
            .filter(ElfisSmartMigrationBatchItem.smart_run_id == run.id)
            .filter(ElfisSmartMigrationBatchItem.status == BatchItemStatus.FAILED.value)
            .count()
        )
        pending_items = (
            self._db.query(ElfisSmartMigrationBatchItem)
            .filter(ElfisSmartMigrationBatchItem.smart_run_id == run.id)
            .filter(ElfisSmartMigrationBatchItem.status == BatchItemStatus.PENDING.value)
            .count()
        )
        if pending_items and run.status != SmartRunStatus.CANCELLED.value:
            run.status = SmartRunStatus.PAUSED.value
        elif failed_items and not pending_items:
            run.status = SmartRunStatus.COMPLETED.value  # partial ok — retry_failed dispo
        else:
            run.status = SmartRunStatus.COMPLETED.value
        run.completed_at = datetime.utcnow()
        run.version = int(run.version or 1) + 1
        self._db.add(run)

        report = self._reporting.generate(
            run, actor_user_id=actor_user_id, formats=["json", "csv", "pdf"]
        )
        publish_smart_migration_event(
            self._db,
            event_type="migration.completed",
            run=run,
            actor_user_id=actor_user_id,
        )
        publish_smart_migration_event(
            self._db,
            event_type="migration.report.ready",
            run=run,
            actor_user_id=actor_user_id,
            metadata={"report_id": report.id, "report_version": report.version},
        )
        self._db.commit()
        self._db.refresh(run)

    def _is_cancelled(self, run_id: str) -> bool:
        row = self._db.get(ElfisSmartMigrationRun, run_id)
        return bool(row and row.status == SmartRunStatus.CANCELLED.value)
