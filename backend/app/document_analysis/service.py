"""Service métier — Document Analysis Pipeline V1."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_analysis import ANALYSIS_VERSION, REPORT_SCHEMA_VERSION
from app.document_analysis.enums import AnalysisReportStatus
from app.document_analysis.events import publish_analysis_event
from app.document_analysis.exceptions import (
    DocumentAnalysisConflictError,
    DocumentAnalysisNotFoundError,
    DocumentAnalysisValidationError,
)
from app.document_analysis.models import ElfisDocumentAnalysisReport
from app.document_analysis.pipeline import PIPELINE_STEPS, run_analysis_pipeline
from app.document_analysis.repository import DocumentAnalysisRepository
from app.document_intake.enums import DocumentLifecycleStatus, LifecycleActorType
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.document_intake.models import ElfisDocumentIntakeItem
from app.document_intake.repository import DocumentIntakeRepository
from app.document_intake.storage import get_storage_provider

logger = logging.getLogger(__name__)

_ANALYZABLE = frozenset(
    {
        DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
        DocumentLifecycleStatus.ANALYSIS_PENDING.value,
        DocumentLifecycleStatus.ANALYZING.value,
        DocumentLifecycleStatus.CLASSIFIED.value,
        DocumentLifecycleStatus.READY_FOR_AI.value,
        DocumentLifecycleStatus.FAILED.value,
    }
)


class DocumentAnalysisService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = DocumentAnalysisRepository(db)
        self._intake = DocumentIntakeRepository(db)
        self._lifecycle = DocumentLifecycleService(db)
        self._storage = get_storage_provider()

    def get_report(
        self, report_id: str, organization_id: int
    ) -> ElfisDocumentAnalysisReport:
        row = self._repo.get_for_org(report_id, organization_id)
        if not row:
            raise DocumentAnalysisNotFoundError("not_found", "Rapport introuvable")
        return row

    def get_latest_for_item(
        self, item_id: str, organization_id: int
    ) -> ElfisDocumentAnalysisReport:
        row = self._repo.get_latest_for_item(
            organization_id=organization_id, document_intake_item_id=item_id
        )
        if not row:
            raise DocumentAnalysisNotFoundError("not_found", "Rapport introuvable")
        return row

    def list_for_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ElfisDocumentAnalysisReport], int]:
        return self._repo.list_for_session(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            limit=limit,
            offset=offset,
        )

    def _load_item(self, item_id: str, organization_id: int) -> ElfisDocumentIntakeItem:
        item = self._intake.get_for_org(item_id, organization_id)
        if not item:
            raise DocumentAnalysisNotFoundError("not_found", "Document introuvable")
        return item

    def _read_bytes(self, item: ElfisDocumentIntakeItem) -> bytes:
        key = item.storage_object_key or item.storage_key
        if not key:
            raise DocumentAnalysisValidationError(
                "storage_missing", "Fichier absent du stockage"
            )
        try:
            with self._storage.get_stream(
                organization_id=item.organization_id, object_key=key
            ) as stream:
                return stream.read()
        except Exception as exc:
            raise DocumentAnalysisValidationError(
                "storage_read_failed", "Impossible de lire le fichier"
            ) from exc

    def analyze_item(
        self,
        item_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        force: bool = False,
    ) -> ElfisDocumentAnalysisReport:
        item = self._load_item(item_id, organization_id)
        status = item.lifecycle_status or item.status

        # Quarantaine / rejeté : jamais d'analyse
        if status in (
            DocumentLifecycleStatus.QUARANTINED.value,
            DocumentLifecycleStatus.REJECTED.value,
            DocumentLifecycleStatus.CANCELLED.value,
        ):
            raise DocumentAnalysisConflictError(
                "not_analyzable",
                "Document non éligible à l'analyse",
            )

        if status == DocumentLifecycleStatus.READY_FOR_AI.value and not force:
            existing = self._repo.get_latest_for_item(
                organization_id=organization_id, document_intake_item_id=item_id
            )
            if existing and existing.status == AnalysisReportStatus.COMPLETED.value:
                return existing

        if status not in _ANALYZABLE and status != DocumentLifecycleStatus.DUPLICATE.value:
            # validated ZIP etc. — permettre si ready via duplicate path
            if status != DocumentLifecycleStatus.VALIDATED.value:
                raise DocumentAnalysisConflictError(
                    "invalid_lifecycle",
                    f"Statut incompatible pour analyse: {status}",
                )
            # validated (ex. ZIP) → ready_for_analysis d'abord
            self._lifecycle.mark_ready_for_analysis(
                item,
                organization_id=organization_id,
                reason_code="analysis_requested",
                actor_type=LifecycleActorType.USER.value
                if actor_user_id
                else LifecycleActorType.SYSTEM.value,
                actor_user_id=actor_user_id,
                commit=False,
            )
            status = item.lifecycle_status

        if status == DocumentLifecycleStatus.DUPLICATE.value:
            self._lifecycle.mark_ready_for_analysis(
                item,
                organization_id=organization_id,
                reason_code="analysis_of_duplicate",
                actor_user_id=actor_user_id,
                commit=False,
            )

        now = datetime.utcnow()
        report = ElfisDocumentAnalysisReport(
            id=str(uuid4()),
            organization_id=organization_id,
            document_intake_item_id=item.id,
            universal_document_id=item.universal_document_id,
            migration_session_id=item.migration_session_id,
            status=AnalysisReportStatus.PENDING.value,
            schema_version=REPORT_SCHEMA_VERSION,
            analysis_version=ANALYSIS_VERSION,
            report_json={},
            warnings_json=[],
            steps_total=len(PIPELINE_STEPS),
            steps_completed=0,
            current_step=PIPELINE_STEPS[0],
            started_at=now,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self._repo.add(report, commit=False)

        actor_kw = {
            "organization_id": organization_id,
            "actor_type": LifecycleActorType.USER.value
            if actor_user_id
            else LifecycleActorType.SYSTEM.value,
            "actor_user_id": actor_user_id,
            "commit": False,
        }

        cur = item.lifecycle_status or item.status
        advance_lifecycle = cur in (
            DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
            DocumentLifecycleStatus.ANALYSIS_PENDING.value,
            DocumentLifecycleStatus.ANALYZING.value,
            DocumentLifecycleStatus.CLASSIFIED.value,
            DocumentLifecycleStatus.VALIDATED.value,
            DocumentLifecycleStatus.DUPLICATE.value,
        )

        if advance_lifecycle:
            if cur == DocumentLifecycleStatus.READY_FOR_ANALYSIS.value:
                self._lifecycle.mark_analysis_pending(
                    item, reason_code="analysis_start", **actor_kw
                )
            cur = item.lifecycle_status or item.status
            if cur == DocumentLifecycleStatus.ANALYSIS_PENDING.value:
                self._lifecycle.mark_analyzing(item, reason_code="pipeline_run", **actor_kw)

        report.status = AnalysisReportStatus.RUNNING.value
        self._repo.save(report, commit=False)

        publish_analysis_event(
            self._db,
            event_type="document.analysis.started",
            report=report,
            actor_user_id=actor_user_id,
            idempotency_key=f"document:analysis:started:{report.id}",
            commit=False,
        )
        self._db.commit()
        self._db.refresh(report)
        self._db.refresh(item)

        try:
            content = self._read_bytes(item)

            def on_step(name: str, idx: int, total: int) -> None:
                report.current_step = name
                report.steps_completed = idx
                report.steps_total = total
                report.updated_at = datetime.utcnow()
                self._db.flush()

            result = run_analysis_pipeline(
                content=content,
                filename=item.original_filename or item.normalized_filename,
                mime=item.detected_mime or item.mime,
                extension=item.extension,
                checksum_sha256=item.checksum_sha256,
                fingerprint=item.fingerprint if isinstance(item.fingerprint, dict) else {},
                size_bytes=int(item.size_bytes or len(content)),
                on_step=on_step,
            )

            report.report_json = result
            report.need_ocr = bool((result.get("ocr_decision") or {}).get("need_ocr"))
            report.classification_label = (result.get("classification") or {}).get("label")
            report.classification_confidence = (result.get("classification") or {}).get(
                "confidence"
            )
            report.language_code = (result.get("language") or {}).get("code")
            report.language_confidence = (result.get("language") or {}).get("confidence")
            report.quality_score = (result.get("quality") or {}).get("score")
            report.orientation_degrees = (result.get("orientation") or {}).get("degrees")
            report.page_count = (result.get("pages") or {}).get("page_count")
            report.detected_format = (result.get("technical") or {}).get("detected_format")
            report.warnings_json = list(result.get("warnings") or [])
            report.processing_time_ms = result.get("processing_time_ms")
            report.status = AnalysisReportStatus.COMPLETED.value
            report.completed_at = datetime.utcnow()
            report.current_step = "ready_for_ai"
            report.steps_completed = len(PIPELINE_STEPS)
            report.version = int(report.version or 1) + 1
            self._repo.save(report, commit=False)

            # Lifecycle → classified → ready_for_ai
            if advance_lifecycle:
                cur = item.lifecycle_status or item.status
                if cur == DocumentLifecycleStatus.ANALYZING.value:
                    self._lifecycle.mark_classified(
                        item, reason_code="heuristic_classification", **actor_kw
                    )
                if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.CLASSIFIED.value:
                    self._lifecycle.mark_ready_for_ai(
                        item, reason_code="prepared_for_ai", **actor_kw
                    )
            # analysis_allowed reste False (pas d'IA lancée) mais document prêt
            item.analysis_allowed = False
            self._db.flush()

            publish_analysis_event(
                self._db,
                event_type="document.analysis.completed",
                report=report,
                actor_user_id=actor_user_id,
                metadata={
                    "classification_label": report.classification_label,
                    "need_ocr": report.need_ocr,
                },
                idempotency_key=f"document:analysis:completed:{report.id}",
                commit=False,
            )
            publish_analysis_event(
                self._db,
                event_type="document.analysis.ready_for_ai",
                report=report,
                actor_user_id=actor_user_id,
                idempotency_key=f"document:analysis:ready_for_ai:{report.id}",
                commit=False,
            )
            self._db.commit()
            self._db.refresh(report)
            return report

        except Exception as exc:
            logger.exception("document_analysis_failed")
            report.status = AnalysisReportStatus.FAILED.value
            report.error_code = getattr(exc, "code", None) or type(exc).__name__
            report.error_message = str(getattr(exc, "message", None) or exc)[:500]
            report.completed_at = datetime.utcnow()
            self._repo.save(report, commit=False)
            try:
                if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.ANALYZING.value:
                    self._lifecycle.mark_failed(
                        item, reason_code="analysis_failed", **actor_kw
                    )
            except Exception:
                item.status = DocumentLifecycleStatus.FAILED.value
                item.lifecycle_status = DocumentLifecycleStatus.FAILED.value
            publish_analysis_event(
                self._db,
                event_type="document.analysis.failed",
                report=report,
                actor_user_id=actor_user_id,
                metadata={"error_code": report.error_code},
                idempotency_key=f"document:analysis:failed:{report.id}",
                commit=False,
            )
            self._db.commit()
            self._db.refresh(report)
            if isinstance(exc, (DocumentAnalysisValidationError, DocumentAnalysisConflictError)):
                raise
            raise DocumentAnalysisValidationError(
                "analysis_failed", report.error_message or "Analyse échouée"
            ) from exc

    def analyze_migration_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        items, _ = self._intake.list_items(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            limit=limit,
            offset=0,
        )
        results: list[ElfisDocumentAnalysisReport] = []
        errors: list[dict[str, str]] = []
        for item in items:
            st = item.lifecycle_status or item.status
            if st in (
                DocumentLifecycleStatus.QUARANTINED.value,
                DocumentLifecycleStatus.CANCELLED.value,
                DocumentLifecycleStatus.REJECTED.value,
            ):
                continue
            if st not in (
                DocumentLifecycleStatus.READY_FOR_ANALYSIS.value,
                DocumentLifecycleStatus.VALIDATED.value,
                DocumentLifecycleStatus.DUPLICATE.value,
                DocumentLifecycleStatus.FAILED.value,
                DocumentLifecycleStatus.READY_FOR_AI.value,
            ):
                # Skip mid-pipeline oddities unless ready/failed
                if st not in (
                    DocumentLifecycleStatus.ANALYSIS_PENDING.value,
                    DocumentLifecycleStatus.ANALYZING.value,
                    DocumentLifecycleStatus.CLASSIFIED.value,
                ):
                    continue
            try:
                results.append(
                    self.analyze_item(
                        item.id,
                        organization_id,
                        actor_user_id=actor_user_id,
                        force=False,
                    )
                )
            except Exception as exc:
                errors.append(
                    {
                        "item_id": item.id,
                        "code": getattr(exc, "code", "error"),
                        "message": str(getattr(exc, "message", exc)),
                    }
                )
        return {
            "analyzed": len(results),
            "errors": errors,
            "reports": results,
        }
