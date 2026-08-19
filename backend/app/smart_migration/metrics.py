"""Métriques Smart Migration — compatible Prometheus via MetricsRegistry."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.models import ElfisDocumentIntakeItem
from app.import_engine.enums import ImportRunStatus
from app.import_engine.models import ElfisImportRun
from app.observability.metrics import metrics_registry
from app.smart_migration.models import (
    ElfisSmartMigrationBatchItem,
    ElfisSmartMigrationRun,
)
from app.validation_mapping.enums import FieldValidationStatus
from app.validation_mapping.models import ElfisValidationField, ElfisValidationSession


# Coûts estimés unitaires (EUR) — calibration Enterprise
COST_OCR_PER_DOC = 0.02
COST_AI_PER_DOC = 0.08


class SmartMigrationMetrics:
    def __init__(self, db: Session):
        self._db = db

    def collect(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        smart_run: ElfisSmartMigrationRun | None = None,
    ) -> dict[str, Any]:
        labels = {
            "organization_id": str(organization_id),
            "migration_id": migration_session_id,
        }
        if smart_run:
            labels["smart_run_id"] = smart_run.id
            if smart_run.correlation_id:
                labels["correlation_id"] = smart_run.correlation_id

        items = (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.migration_session_id == migration_session_id)
            .all()
        )
        imports = (
            self._db.query(ElfisImportRun)
            .filter(ElfisImportRun.organization_id == organization_id)
            .filter(ElfisImportRun.migration_session_id == migration_session_id)
            .all()
        )
        durations = [int(r.duration_ms or 0) for r in imports if r.duration_ms]
        batch_items = []
        if smart_run:
            batch_items = (
                self._db.query(ElfisSmartMigrationBatchItem)
                .filter(ElfisSmartMigrationBatchItem.smart_run_id == smart_run.id)
                .all()
            )
            durations.extend(
                int(i.duration_ms or 0) for i in batch_items if i.duration_ms
            )

        retries = sum(max(0, int(i.attempts or 0) - 1) for i in batch_items)
        errors = sum(
            1
            for it in items
            if (it.lifecycle_status or it.status)
            in {
                DocumentLifecycleStatus.FAILED.value,
                DocumentLifecycleStatus.IMPORT_FAILED.value,
                DocumentLifecycleStatus.REJECTED.value,
            }
        )
        rejected = sum(
            1
            for it in items
            if (it.lifecycle_status or it.status)
            == DocumentLifecycleStatus.REJECTED.value
        )
        imported = sum(
            1
            for r in imports
            if r.status == ImportRunStatus.COMPLETED.value
        )

        # OCR / IA : heuristique sur cycle de vie (pas de re-run pipeline)
        ocr_used = sum(
            1
            for it in items
            if (it.lifecycle_status or "")
            in {
                DocumentLifecycleStatus.OCR_PENDING.value,
                DocumentLifecycleStatus.OCR_PROCESSING.value,
                DocumentLifecycleStatus.OCR_COMPLETED.value,
                DocumentLifecycleStatus.READY_FOR_AI.value,
                DocumentLifecycleStatus.EXTRACTED.value,
                DocumentLifecycleStatus.AWAITING_VALIDATION.value,
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
                DocumentLifecycleStatus.IMPORT_COMPLETED.value,
                DocumentLifecycleStatus.IMPORTED.value,
            }
            or True  # intake analysé compte comme OCR/IA path
        )
        # Plus précis : documents ayant dépassé ready_for_ai
        ocr_used = sum(
            1
            for it in items
            if self._past(it.lifecycle_status or "", DocumentLifecycleStatus.READY_FOR_AI.value)
        )
        ai_used = ocr_used

        sessions = (
            self._db.query(ElfisValidationSession)
            .filter(ElfisValidationSession.organization_id == organization_id)
            .filter(ElfisValidationSession.migration_session_id == migration_session_id)
            .all()
        )
        session_ids = [s.id for s in sessions]
        corrected = 0
        if session_ids:
            corrected = (
                self._db.query(ElfisValidationField)
                .filter(ElfisValidationField.validation_session_id.in_(session_ids))
                .filter(
                    ElfisValidationField.status == FieldValidationStatus.EDITED.value
                )
                .count()
            )

        avg_ms = (sum(durations) / len(durations)) if durations else 0.0
        max_ms = float(max(durations)) if durations else 0.0
        min_ms = float(min(durations)) if durations else 0.0
        elapsed_min = 1.0
        if smart_run and smart_run.started_at:
            elapsed_min = max(
                (datetime.utcnow() - smart_run.started_at).total_seconds() / 60.0,
                0.01,
            )
        throughput = imported / elapsed_min if elapsed_min else 0.0

        estimated_cost = round(
            ocr_used * COST_OCR_PER_DOC + ai_used * COST_AI_PER_DOC, 4
        )
        actual_cost = float(smart_run.actual_cost) if smart_run else estimated_cost

        metrics = {
            "avg_duration_ms": round(avg_ms, 2),
            "max_duration_ms": max_ms,
            "min_duration_ms": min_ms,
            "throughput_per_min": round(throughput, 3),
            "retries": retries,
            "errors": errors,
            "ocr_used": ocr_used,
            "ai_used": ai_used,
            "documents_rejected": rejected,
            "documents_corrected": corrected,
            "documents_imported": imported,
            "documents_total": len(items),
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "correlation_id": smart_run.correlation_id if smart_run else None,
            "migration_id": migration_session_id,
            "batch_id": None,
            "computed_at": datetime.utcnow().isoformat() + "Z",
        }

        # Registry Prometheus-compatible
        metrics_registry.set_gauge(
            "smart_migration_progress_percent",
            float(smart_run.progress_percent if smart_run else 0),
            labels=labels,
        )
        metrics_registry.set_gauge(
            "smart_migration_throughput_per_min", throughput, labels=labels
        )
        metrics_registry.incr(
            "smart_migration_documents_imported_total",
            value=0,  # gauge-like via set
            labels=labels,
        )
        metrics_registry.set_gauge(
            "smart_migration_documents_imported", float(imported), labels=labels
        )
        metrics_registry.set_gauge(
            "smart_migration_estimated_cost", estimated_cost, labels=labels
        )
        if durations:
            metrics_registry.observe(
                "smart_migration_document_duration_ms", avg_ms, labels=labels
            )

        if smart_run:
            smart_run.metrics_json = metrics
            smart_run.estimated_cost = estimated_cost
            smart_run.actual_cost = actual_cost
            smart_run.throughput_per_min = throughput
            remaining = max(
                int(smart_run.documents_total or 0)
                - int(smart_run.documents_completed or 0),
                0,
            )
            smart_run.eta_seconds = (
                (remaining / throughput) * 60.0 if throughput > 0 else None
            )
            self._db.add(smart_run)
            self._db.flush()

        return metrics

    @staticmethod
    def _past(current: str, milestone: str) -> bool:
        order = [
            DocumentLifecycleStatus.UPLOADED.value,
            DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            DocumentLifecycleStatus.READY_FOR_AI.value,
            DocumentLifecycleStatus.EXTRACTED.value,
            DocumentLifecycleStatus.AWAITING_VALIDATION.value,
            DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            DocumentLifecycleStatus.IMPORT_COMPLETED.value,
            DocumentLifecycleStatus.IMPORTED.value,
        ]
        try:
            return order.index(current) >= order.index(milestone)
        except ValueError:
            return current in {
                DocumentLifecycleStatus.IMPORT_COMPLETED.value,
                DocumentLifecycleStatus.IMPORTED.value,
                DocumentLifecycleStatus.EXTRACTED.value,
                DocumentLifecycleStatus.READY_FOR_IMPORT.value,
            }
