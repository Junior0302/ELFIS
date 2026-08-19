"""Service métier — Document Extraction Engine V1."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_analysis.repository import DocumentAnalysisRepository
from app.document_extraction import EXTRACTION_ENGINE_VERSION, PROMPT_VERSION
from app.document_extraction.document_types import get_schema
from app.document_extraction.eligibility import ExtractionEligibilityService
from app.document_extraction.enums import ExtractionStatus
from app.document_extraction.events import publish_extraction_event
from app.document_extraction.exceptions import (
    DocumentExtractionConflictError,
    DocumentExtractionIneligibleError,
    DocumentExtractionNotFoundError,
)
from app.document_extraction.models import (
    ElfisDocumentExtraction,
    ElfisDocumentExtractionAttempt,
)
from app.document_extraction.pipeline import compute_input_fingerprint, run_extraction_pipeline
from app.document_extraction.repository import DocumentExtractionRepository
from sqlalchemy.exc import IntegrityError
from app.document_intake.enums import DocumentLifecycleStatus, LifecycleActorType
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.document_intake.repository import DocumentIntakeRepository
from app.document_intake.storage import get_storage_provider

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = DocumentExtractionRepository(db)
        self._intake = DocumentIntakeRepository(db)
        self._analysis = DocumentAnalysisRepository(db)
        self._lifecycle = DocumentLifecycleService(db)
        self._eligibility = ExtractionEligibilityService(db)
        self._storage = get_storage_provider()

    def get_extraction(
        self, extraction_id: str, organization_id: int
    ) -> ElfisDocumentExtraction:
        row = self._repo.get_for_org(extraction_id, organization_id)
        if not row:
            raise DocumentExtractionNotFoundError("not_found", "Extraction introuvable")
        return row

    def list_for_document(
        self, document_id: str, organization_id: int
    ) -> list[ElfisDocumentExtraction]:
        item = self._intake.get_for_org(document_id, organization_id)
        if not item:
            raise DocumentExtractionNotFoundError("not_found", "Document introuvable")
        return self._repo.list_for_item(
            organization_id=organization_id, document_intake_item_id=document_id
        )

    def list_for_session(
        self, *, organization_id: int, migration_session_id: str
    ) -> list[ElfisDocumentExtraction]:
        return self._repo.list_for_session(
            organization_id=organization_id, migration_session_id=migration_session_id
        )

    def start_extraction(
        self,
        document_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        force_reextract: bool = False,
        schema_name: str | None = None,
        sync: bool = True,
    ) -> ElfisDocumentExtraction:
        item = self._intake.get_for_org(document_id, organization_id)
        if not item:
            raise DocumentExtractionNotFoundError("not_found", "Document introuvable")

        analysis = self._analysis.get_latest_for_item(
            organization_id=organization_id, document_intake_item_id=item.id
        )
        if not analysis:
            raise DocumentExtractionIneligibleError(
                "ANALYSIS_MISSING", "Rapport d'analyse manquant"
            )

        report = dict(analysis.report_json or {})
        report.setdefault("analysis_version", analysis.analysis_version)
        doc_type = analysis.classification_label or (
            (report.get("classification") or {}).get("label")
        )
        schema = get_schema(schema_name, doc_type)
        fp = compute_input_fingerprint(
            document_checksum=item.checksum_sha256 or "",
            analysis_version=str(analysis.analysis_version or "1"),
            schema_name=schema["schema_name"],
            schema_version=schema["schema_version"],
            extractor_version=EXTRACTION_ENGINE_VERSION,
            prompt_version=PROMPT_VERSION,
        )

        # Idempotence avant éligibilité (document peut déjà être awaiting_validation)
        if not force_reextract:
            existing = self._repo.find_by_fingerprint(
                organization_id=organization_id, input_fingerprint=fp
            )
            if existing:
                return existing

        try:
            self._eligibility.assert_eligible(
                item, organization_id=organization_id, for_start=True
            )
        except DocumentExtractionIneligibleError:
            if force_reextract and (item.lifecycle_status or item.status) in (
                DocumentLifecycleStatus.AWAITING_VALIDATION.value,
                DocumentLifecycleStatus.EXTRACTED.value,
                DocumentLifecycleStatus.FAILED.value,
                DocumentLifecycleStatus.OCR_PENDING.value,
            ):
                pass
            else:
                raise

        if force_reextract:
            for old in self._repo.list_for_item(
                organization_id=organization_id, document_intake_item_id=item.id
            ):
                if old.status_scope == "active":
                    old.status = ExtractionStatus.SUPERSEDED.value
                    # Unique (org, fingerprint, scope) — scope fermé doit être unique
                    old.status_scope = f"closed:{old.id}"
                    self._repo.save(old, commit=False)

        now = datetime.utcnow()
        row = ElfisDocumentExtraction(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=item.migration_session_id,
            document_intake_item_id=item.id,
            universal_document_id=item.universal_document_id,
            analysis_report_id=analysis.id,
            schema_name=schema["schema_name"],
            schema_version=schema["schema_version"],
            extraction_version=EXTRACTION_ENGINE_VERSION,
            status=ExtractionStatus.PENDING.value,
            status_scope="active",
            prompt_version=PROMPT_VERSION,
            input_fingerprint=fp,
            structured_data={},
            field_provenance={},
            quality_summary={},
            warnings_json=[],
            errors_json=[],
            requires_human_review=True,
            progress_percent=0,
            current_step="eligibility",
            created_by_user_id=actor_user_id,
            started_at=now,
            created_at=now,
            updated_at=now,
            version=1,
        )
        self._repo.add(row, commit=False)
        publish_extraction_event(
            self._db,
            event_type="document.extraction.requested",
            extraction=row,
            actor_user_id=actor_user_id,
            commit=False,
        )
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            # Course concurrente : reprendre l'extraction active existante
            existing = self._repo.find_by_fingerprint(
                organization_id=organization_id, input_fingerprint=fp
            )
            if existing:
                return existing
            # Tentative running (pending/queued...)
            racing = (
                self._db.query(ElfisDocumentExtraction)
                .filter(ElfisDocumentExtraction.organization_id == organization_id)
                .filter(ElfisDocumentExtraction.input_fingerprint == fp)
                .filter(ElfisDocumentExtraction.status_scope == "active")
                .order_by(ElfisDocumentExtraction.created_at.asc())
                .first()
            )
            if racing:
                return racing
            raise DocumentExtractionConflictError(
                "concurrent_conflict", "Conflit concurrent d'extraction"
            )
        self._db.refresh(row)

        if sync:
            return self._run(row.id, organization_id, actor_user_id=actor_user_id)
        # Async: enqueue job
        row.status = ExtractionStatus.QUEUED.value
        self._repo.save(row, commit=True)
        publish_extraction_event(
            self._db,
            event_type="document.extraction.queued",
            extraction=row,
            actor_user_id=actor_user_id,
        )
        try:
            from app.jobs.job_schemas import JobRequest
            from app.jobs.job_service import JobService
            from app.jobs.job_types import JobNames

            JobService(self._db).enqueue(
                JobRequest(
                    job_name=JobNames.DOCUMENT_EXTRACTION_RUN,
                    organization_id=organization_id,
                    user_id=actor_user_id,
                    payload={
                        "extraction_id": row.id,
                        "document_intake_item_id": item.id,
                        "universal_document_id": item.universal_document_id,
                        "migration_session_id": item.migration_session_id,
                    },
                    idempotency_key=f"document-extraction:{row.id}",
                )
            )
        except Exception:
            logger.exception("extraction_enqueue_failed")
            return self._run(row.id, organization_id, actor_user_id=actor_user_id)
        return row

    def _run(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
    ) -> ElfisDocumentExtraction:
        row = self.get_extraction(extraction_id, organization_id)
        item = self._intake.get_for_org(row.document_intake_item_id, organization_id)
        if not item:
            raise DocumentExtractionNotFoundError("not_found", "Document introuvable")
        analysis = self._analysis.get_latest_for_item(
            organization_id=organization_id, document_intake_item_id=item.id
        )
        report = dict((analysis.report_json if analysis else None) or {})

        actor_kw = {
            "organization_id": organization_id,
            "actor_type": LifecycleActorType.USER.value
            if actor_user_id
            else LifecycleActorType.SYSTEM.value,
            "actor_user_id": actor_user_id,
            "commit": False,
        }

        cur = item.lifecycle_status or item.status
        if cur == DocumentLifecycleStatus.READY_FOR_AI.value:
            # OCR branch decided after text resolve
            pass

        row.status = ExtractionStatus.PREPARING.value
        row.progress_percent = 5
        self._repo.save(row, commit=False)
        publish_extraction_event(
            self._db,
            event_type="document.extraction.started",
            extraction=row,
            actor_user_id=actor_user_id,
            commit=False,
        )
        self._db.commit()

        attempt = ElfisDocumentExtractionAttempt(
            id=str(uuid4()),
            organization_id=organization_id,
            extraction_id=row.id,
            attempt_number=1,
            extractor_name="pipeline",
            status="running",
            started_at=datetime.utcnow(),
            input_metadata={"schema_name": row.schema_name},
        )
        self._repo.add_attempt(attempt, commit=False)

        try:
            key = item.storage_object_key or item.storage_key
            with self._storage.get_stream(
                organization_id=organization_id, object_key=key
            ) as stream:
                content = stream.read()

            from app.document_extraction.text_resolver import resolve_document_text

            pre = resolve_document_text(
                content=content,
                filename=item.original_filename or item.normalized_filename,
                mime=item.detected_mime or item.mime,
                extension=item.extension,
                analysis_report=report,
                need_ocr=analysis.need_ocr if analysis else None,
            )
            if pre.get("requires_ocr") and not (pre.get("text") or "").strip():
                row.status = ExtractionStatus.OCR_PENDING.value
                row.warnings_json = list(pre.get("warnings") or []) + ["ocr_required"]
                row.progress_percent = 15
                row.text_source = pre.get("source")
                row.completed_at = datetime.utcnow()
                self._repo.save(row, commit=False)
                if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.READY_FOR_AI.value:
                    self._lifecycle.mark_ocr_pending(
                        item, reason_code="ocr_required", **actor_kw
                    )
                attempt.status = "ocr_pending"
                attempt.completed_at = datetime.utcnow()
                self._db.commit()
                self._db.refresh(row)
                return row

            def on_progress(step: str, pct: int) -> None:
                row.current_step = step
                row.progress_percent = pct
                row.status = ExtractionStatus.EXTRACTING.value
                self._db.flush()

            cur = item.lifecycle_status or item.status
            if cur == DocumentLifecycleStatus.READY_FOR_AI.value:
                self._lifecycle.mark_extraction_pending(
                    item, reason_code="extraction_start", **actor_kw
                )
            if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.EXTRACTION_PENDING.value:
                self._lifecycle.mark_extracting(item, reason_code="pipeline", **actor_kw)

            result = run_extraction_pipeline(
                content=content,
                filename=item.original_filename or item.normalized_filename,
                mime=item.detected_mime or item.mime,
                extension=item.extension,
                checksum_sha256=item.checksum_sha256 or "",
                analysis_report=report,
                need_ocr=analysis.need_ocr if analysis else None,
                document_type=analysis.classification_label if analysis else None,
                organization_id=organization_id,
                db=self._db,
                schema_name=row.schema_name,
                on_progress=on_progress,
            )

            qs = result.get("quality_summary") or {}
            row.structured_data = result.get("structured_data") or {}
            row.field_provenance = result.get("field_provenance") or {}
            row.quality_summary = qs
            row.warnings_json = list(result.get("warnings") or [])
            row.errors_json = list(result.get("errors") or [])
            row.overall_confidence = qs.get("overall_confidence")
            row.critical_fields_confidence = qs.get("critical_fields_confidence")
            row.completeness_score = qs.get("completeness_score")
            row.consistency_score = qs.get("consistency_score")
            row.confidence_level = qs.get("confidence_level")
            row.requires_human_review = True
            row.strategy = result.get("strategy")
            row.provider = (result.get("llm_meta") or {}).get("provider")
            row.model_name = (result.get("llm_meta") or {}).get("model_name")
            row.text_source = (result.get("text_info") or {}).get("source")
            row.text_character_count = (result.get("text_info") or {}).get("character_count")
            row.progress_percent = 100
            row.current_step = "completed"
            row.completed_at = datetime.utcnow()
            row.version = int(row.version or 1) + 1

            useful = bool(row.structured_data) and (row.completeness_score or 0) > 0.05
            if not useful or result.get("status") == "failed":
                row.status = ExtractionStatus.FAILED.value
                row.failed_at = datetime.utcnow()
                row.status_scope = f"closed:{row.id}"
                try:
                    if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.EXTRACTING.value:
                        self._lifecycle.mark_failed(
                            item, reason_code="extraction_empty", **actor_kw
                        )
                except Exception:
                    pass
                publish_extraction_event(
                    self._db,
                    event_type="document.extraction.failed",
                    extraction=row,
                    actor_user_id=actor_user_id,
                    commit=False,
                )
            else:
                if row.warnings_json or row.errors_json:
                    row.status = ExtractionStatus.COMPLETED_WITH_WARNINGS.value
                    evt = "document.extraction.completed_with_warnings"
                else:
                    row.status = ExtractionStatus.COMPLETED.value
                    evt = "document.extraction.completed"
                publish_extraction_event(
                    self._db,
                    event_type=evt,
                    extraction=row,
                    actor_user_id=actor_user_id,
                    commit=False,
                )
                # Lifecycle → extracted → awaiting_validation
                if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.EXTRACTING.value:
                    self._lifecycle.mark_extracted(
                        item, reason_code="extraction_done", **actor_kw
                    )
                if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.EXTRACTED.value:
                    self._lifecycle.mark_awaiting_validation(
                        item, reason_code="human_review_required", **actor_kw
                    )
                row.status = ExtractionStatus.AWAITING_HUMAN_VALIDATION.value
                publish_extraction_event(
                    self._db,
                    event_type="document.extraction.awaiting_validation",
                    extraction=row,
                    actor_user_id=actor_user_id,
                    commit=False,
                )

            attempt.status = "completed"
            attempt.completed_at = datetime.utcnow()
            attempt.output_metadata = {
                "strategy": row.strategy,
                "fields": len(row.field_provenance or {}),
            }
            self._repo.save(row, commit=False)
            self._db.commit()
            self._db.refresh(row)
            return row

        except Exception as exc:
            logger.exception("document_extraction_failed")
            row.status = ExtractionStatus.FAILED.value
            row.failed_at = datetime.utcnow()
            row.status_scope = f"closed:{row.id}"
            row.errors_json = [{"code": type(exc).__name__, "message": str(exc)[:200]}]
            attempt.status = "failed"
            attempt.error_code = type(exc).__name__
            attempt.error_message_safe = type(exc).__name__
            attempt.completed_at = datetime.utcnow()
            try:
                if (item.lifecycle_status or item.status) == DocumentLifecycleStatus.EXTRACTING.value:
                    self._lifecycle.mark_failed(
                        item, reason_code="extraction_failed", **actor_kw
                    )
            except Exception:
                pass
            publish_extraction_event(
                self._db,
                event_type="document.extraction.failed",
                extraction=row,
                actor_user_id=actor_user_id,
                commit=False,
            )
            self._repo.save(row, commit=True)
            raise

    def extract_migration_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        actor_user_id: int | None = None,
        limit: int = 100,
    ) -> dict:
        items, _ = self._intake.list_items(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            limit=limit,
            offset=0,
        )
        results: list[ElfisDocumentExtraction] = []
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
                DocumentLifecycleStatus.READY_FOR_AI.value,
                DocumentLifecycleStatus.FAILED.value,
                DocumentLifecycleStatus.OCR_PENDING.value,
            ):
                continue
            try:
                results.append(
                    self.start_extraction(
                        item.id,
                        organization_id,
                        actor_user_id=actor_user_id,
                        sync=True,
                    )
                )
            except DocumentExtractionIneligibleError as exc:
                errors.append(
                    {"item_id": item.id, "code": exc.code, "message": exc.message}
                )
            except Exception as exc:
                errors.append(
                    {
                        "item_id": item.id,
                        "code": type(exc).__name__,
                        "message": str(exc)[:200],
                    }
                )
        return {"extracted": len(results), "errors": errors, "items": results}

    def retry_extraction(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
    ) -> ElfisDocumentExtraction:
        old = self.get_extraction(extraction_id, organization_id)
        return self.start_extraction(
            old.document_intake_item_id,
            organization_id,
            actor_user_id=actor_user_id,
            force_reextract=True,
            schema_name=old.schema_name,
            sync=True,
        )

    def cancel_extraction(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
    ) -> ElfisDocumentExtraction:
        row = self.get_extraction(extraction_id, organization_id)
        if row.status in (
            ExtractionStatus.COMPLETED.value,
            ExtractionStatus.AWAITING_HUMAN_VALIDATION.value,
            ExtractionStatus.CANCELLED.value,
        ):
            if row.status == ExtractionStatus.CANCELLED.value:
                return row
            raise DocumentExtractionConflictError(
                "not_cancellable", "Extraction non annulable"
            )
        row.status = ExtractionStatus.CANCELLED.value
        row.status_scope = f"closed:{row.id}"
        row.completed_at = datetime.utcnow()
        self._repo.save(row, commit=True)
        publish_extraction_event(
            self._db,
            event_type="document.extraction.cancelled",
            extraction=row,
            actor_user_id=actor_user_id,
        )
        return row
