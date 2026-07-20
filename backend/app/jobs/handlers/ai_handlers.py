"""Handlers Job Queue — tâches AI documentaires."""

from __future__ import annotations

from datetime import datetime

from app.ai.ai_schemas import AIExecutionRequest
from app.ai.ai_service import AIService
from app.ai.ai_types import AITaskNames, DocumentAnalysisStatus
from app.ai.ai_repository import AIRepository
from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult, JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.models_vault import VaultDocument


def _load_vault_doc(context: JobContext, vault_document_id: str) -> VaultDocument:
    db = context._db
    own = False
    if db is None and context._session_factory is not None:
        db = context._session_factory()
        own = True
    if db is None:
        raise RetryableJobError("session indisponible")
    try:
        doc = db.query(VaultDocument).filter(VaultDocument.id == vault_document_id).first()
        if not doc:
            raise PermanentJobError(f"document absent: {vault_document_id}")
        if context.organization_id is not None and doc.organization_id != context.organization_id:
            raise PermanentJobError("organization_id mismatch")
        return doc
    finally:
        if own and db is not None:
            db.close()


def _session(context: JobContext):
    if context._db is not None:
        return context._db, False
    if context._session_factory is None:
        raise RetryableJobError("session indisponible")
    return context._session_factory(), True


class DocumentClassificationJobHandler(JobHandler):
    handler_name = "vault_document_ai_classification_v1"
    job_name = JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            raise PermanentJobError("vault_document_id requis")

        context.update_progress(10, "loading_document")
        _load_vault_doc(context, vault_document_id)

        text = str(payload.get("extracted_text") or "").strip()
        filename = str(payload.get("filename") or "document.pdf")
        mime_type = str(payload.get("mime_type") or "application/pdf")
        analysis_id = str(payload.get("analysis_id") or "").strip() or None
        version = int(payload.get("document_version") or 1)

        db, own = _session(context)
        try:
            context.update_progress(40, "classifying")
            result = AIService(db).execute(
                AIExecutionRequest(
                    task_name=AITaskNames.DOCUMENT_CLASSIFY,
                    organization_id=job.organization_id,
                    user_id=job.user_id,
                    input_reference_type="vault_document",
                    input_reference_id=vault_document_id,
                    input_data={
                        "vault_document_id": vault_document_id,
                        "extracted_text": text,
                        "filename": filename,
                        "mime_type": mime_type,
                    },
                    idempotency_key=f"ai-classify-exec:{job.organization_id}:{vault_document_id}:{version}",
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                )
            )
            context.update_progress(80, "updating_analysis")
            if analysis_id:
                repo = AIRepository(db)
                analysis = repo.find_analysis(analysis_id)
                if analysis:
                    ids = list(analysis.ai_execution_ids or [])
                    ids.append(result.execution_id)
                    analysis.ai_execution_ids = ids
                    analysis.classification = result.result
                    analysis.document_type = (result.result or {}).get("document_type")
                    analysis.confidence = result.confidence
                    analysis.requires_review = result.requires_review
                    if result.status == "blocked" or (result.result or {}).get("blocked"):
                        analysis.status = DocumentAnalysisStatus.BLOCKED
                        analysis.current_stage = "awaiting_ocr"
                    else:
                        analysis.status = DocumentAnalysisStatus.EXTRACTING
                        analysis.current_stage = "extraction"
                        # Enqueue extraction si facture
                        doc_type = (result.result or {}).get("document_type")
                        if doc_type in ("customer_invoice", "supplier_invoice") and text:
                            JobService(db).enqueue(
                                JobRequest(
                                    job_name=JobNames.VAULT_DOCUMENT_AI_EXTRACTION,
                                    organization_id=job.organization_id,
                                    user_id=job.user_id,
                                    payload={
                                        "vault_document_id": vault_document_id,
                                        "analysis_id": analysis_id,
                                        "extracted_text": text[:40_000],
                                        "filename": filename,
                                        "document_type": doc_type,
                                        "document_version": version,
                                    },
                                    idempotency_key=(
                                        f"ai-extract-invoice:{job.organization_id}:"
                                        f"{vault_document_id}:{version}"
                                    ),
                                    correlation_id=job.correlation_id,
                                    parent_job_id=job.job_id,
                                )
                            )
                        else:
                            # quality check sans extraction facture
                            JobService(db).enqueue(
                                JobRequest(
                                    job_name=JobNames.VAULT_DOCUMENT_QUALITY_CHECK,
                                    organization_id=job.organization_id,
                                    user_id=job.user_id,
                                    payload={
                                        "vault_document_id": vault_document_id,
                                        "analysis_id": analysis_id,
                                        "extracted_text": text[:40_000],
                                        "filename": filename,
                                        "document_version": version,
                                    },
                                    idempotency_key=(
                                        f"ai-quality:{job.organization_id}:"
                                        f"{vault_document_id}:{version}"
                                    ),
                                    correlation_id=job.correlation_id,
                                    parent_job_id=job.job_id,
                                )
                            )
                            analysis.status = DocumentAnalysisStatus.VALIDATING
                            analysis.current_stage = "validation"
                    analysis.updated_at = datetime.utcnow()
                    repo.save_analysis(analysis)

            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="classification_done",
                result={
                    "execution_id": result.execution_id,
                    "document_type": (result.result or {}).get("document_type"),
                    "confidence": result.confidence,
                    "requires_review": result.requires_review,
                    "analysis_id": analysis_id,
                },
            )
        finally:
            if own:
                db.close()


class DocumentInvoiceExtractionJobHandler(JobHandler):
    handler_name = "vault_document_ai_extraction_v1"
    job_name = JobNames.VAULT_DOCUMENT_AI_EXTRACTION

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            raise PermanentJobError("vault_document_id requis")
        context.update_progress(15, "loading")
        _load_vault_doc(context, vault_document_id)
        text = str(payload.get("extracted_text") or "").strip()
        filename = str(payload.get("filename") or "invoice.pdf")
        analysis_id = str(payload.get("analysis_id") or "").strip() or None
        version = int(payload.get("document_version") or 1)
        doc_type = str(payload.get("document_type") or "supplier_invoice")

        db, own = _session(context)
        try:
            context.update_progress(50, "extracting")
            result = AIService(db).execute(
                AIExecutionRequest(
                    task_name=AITaskNames.DOCUMENT_EXTRACT_INVOICE,
                    organization_id=job.organization_id,
                    user_id=job.user_id,
                    input_reference_type="vault_document",
                    input_reference_id=vault_document_id,
                    input_data={
                        "vault_document_id": vault_document_id,
                        "extracted_text": text,
                        "document_type": doc_type,
                        "filename": filename,
                    },
                    idempotency_key=(
                        f"ai-extract-invoice-exec:{job.organization_id}:"
                        f"{vault_document_id}:{version}"
                    ),
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                )
            )
            if analysis_id:
                repo = AIRepository(db)
                analysis = repo.find_analysis(analysis_id)
                if analysis:
                    ids = list(analysis.ai_execution_ids or [])
                    ids.append(result.execution_id)
                    analysis.ai_execution_ids = ids
                    analysis.extraction = result.result
                    analysis.requires_review = analysis.requires_review or result.requires_review
                    if result.confidence is not None:
                        analysis.confidence = result.confidence
                    analysis.status = DocumentAnalysisStatus.VALIDATING
                    analysis.current_stage = "validation"
                    analysis.updated_at = datetime.utcnow()
                    repo.save_analysis(analysis)
                    JobService(db).enqueue(
                        JobRequest(
                            job_name=JobNames.VAULT_DOCUMENT_QUALITY_CHECK,
                            organization_id=job.organization_id,
                            user_id=job.user_id,
                            payload={
                                "vault_document_id": vault_document_id,
                                "analysis_id": analysis_id,
                                "filename": filename,
                                "document_version": version,
                                "extraction": (result.result or {}).get("compatible_extraction"),
                                "amounts": (result.result or {}).get("amounts"),
                                "invoice": (result.result or {}).get("invoice"),
                                "supplier": (result.result or {}).get("supplier"),
                                "confidence": result.confidence,
                            },
                            idempotency_key=(
                                f"ai-quality:{job.organization_id}:{vault_document_id}:{version}"
                            ),
                            correlation_id=job.correlation_id,
                            parent_job_id=job.job_id,
                        )
                    )
            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="extraction_done",
                result={
                    "execution_id": result.execution_id,
                    "confidence": result.confidence,
                    "needs_review": result.requires_review,
                    "analysis_id": analysis_id,
                },
            )
        finally:
            if own:
                db.close()


class DocumentQualityCheckJobHandler(JobHandler):
    handler_name = "vault_document_quality_check_v1"
    job_name = JobNames.VAULT_DOCUMENT_QUALITY_CHECK

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            raise PermanentJobError("vault_document_id requis")
        context.update_progress(20, "quality_check")
        _load_vault_doc(context, vault_document_id)
        analysis_id = str(payload.get("analysis_id") or "").strip() or None
        version = int(payload.get("document_version") or 1)

        db, own = _session(context)
        try:
            input_data = {
                k: v
                for k, v in payload.items()
                if k
                not in (
                    "pdf",
                    "pdf_base64",
                    "api_key",
                )
            }
            result = AIService(db).execute(
                AIExecutionRequest(
                    task_name=AITaskNames.DOCUMENT_QUALITY_CHECK,
                    organization_id=job.organization_id,
                    user_id=job.user_id,
                    input_reference_type="vault_document",
                    input_reference_id=vault_document_id,
                    input_data=input_data,
                    idempotency_key=(
                        f"ai-quality-exec:{job.organization_id}:{vault_document_id}:{version}"
                    ),
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                )
            )
            if analysis_id:
                repo = AIRepository(db)
                analysis = repo.find_analysis(analysis_id)
                if analysis:
                    ids = list(analysis.ai_execution_ids or [])
                    ids.append(result.execution_id)
                    analysis.ai_execution_ids = ids
                    analysis.quality = result.result
                    analysis.requires_review = analysis.requires_review or result.requires_review
                    if result.confidence is not None:
                        analysis.confidence = result.confidence
                    if result.requires_review or (result.result or {}).get("status") == "invalid":
                        analysis.status = DocumentAnalysisStatus.REQUIRES_REVIEW
                    else:
                        analysis.status = DocumentAnalysisStatus.COMPLETED
                        analysis.completed_at = datetime.utcnow()
                    analysis.current_stage = "completed"
                    analysis.updated_at = datetime.utcnow()
                    repo.save_analysis(analysis)

                    # Événement document.analysis.completed.v1
                    from app.events.event_bus import safe_publish
                    from app.events.event_schemas import DomainEvent
                    from app.events.event_types import EventNames
                    import uuid as _uuid

                    safe_publish(
                        db,
                        DomainEvent(
                            event_name=EventNames.DOCUMENT_ANALYSIS_COMPLETED,
                            organization_id=job.organization_id or 0,
                            aggregate_type="document_analysis",
                            aggregate_id=analysis.analysis_id,
                            payload={
                                "analysis_id": analysis.analysis_id,
                                "vault_document_id": vault_document_id,
                                "status": analysis.status,
                                "document_type": analysis.document_type,
                                "requires_review": analysis.requires_review,
                                "correlation_id": job.correlation_id,
                            },
                            metadata={"source": "ai_quality_job"},
                            correlation_id=_uuid.UUID(job.correlation_id)
                            if job.correlation_id
                            else _uuid.uuid4(),
                        ),
                    )

            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message="quality_done",
                result={
                    "execution_id": result.execution_id,
                    "quality_status": (result.result or {}).get("status"),
                    "requires_review": result.requires_review,
                    "analysis_id": analysis_id,
                },
            )
        finally:
            if own:
                db.close()
