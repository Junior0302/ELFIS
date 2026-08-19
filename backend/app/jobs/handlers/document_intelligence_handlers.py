"""Handlers Job Queue — Document Intelligence."""

from __future__ import annotations

from app.document_intelligence.document_exceptions import (
    DocumentNotFoundError,
    DocumentOCRUnavailableError,
    DocumentValidationError,
)
from app.document_intelligence.document_schemas import DocumentExtractionRequest
from app.document_intelligence.document_service import DocumentIntelligenceService
from app.document_intelligence.document_types import ExtractionStatus
from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandler
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import JobNames


def _session(context: JobContext):
    if context._db is not None:
        return context._db, False
    if context._session_factory is None:
        raise RetryableJobError("session indisponible")
    return context._session_factory(), True


class DocumentTextExtractionJobHandler(JobHandler):
    handler_name = "vault_document_extract_text_v1"
    job_name = JobNames.VAULT_DOCUMENT_EXTRACT_TEXT

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            raise PermanentJobError("vault_document_id requis")
        version = int(payload.get("document_version") or 1)

        context.update_progress(15, "loading_document")
        db, own = _session(context)
        try:
            # Contenu optionnel (tests) — jamais depuis un client HTTP
            content = None
            raw_bytes = payload.get("_test_content_bytes")
            if isinstance(raw_bytes, (bytes, bytearray)):
                content = bytes(raw_bytes)
            else:
                raw_b64 = payload.get("_test_content_b64")
                if isinstance(raw_b64, str) and raw_b64:
                    import base64

                    content = base64.b64decode(raw_b64)

            context.update_progress(40, "extracting")
            svc = DocumentIntelligenceService(db)
            result = svc.extract_document_text(
                DocumentExtractionRequest(
                    organization_id=int(job.organization_id or 0),
                    user_id=job.user_id,
                    vault_document_id=vault_document_id,
                    document_version=version,
                    idempotency_key=str(payload.get("idempotency_key") or "") or None,
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                    content_bytes=content,
                )
            )
            context.update_progress(100, "done")
            return JobExecutionResult(
                status="completed",
                progress=100,
                message=result.status,
                result={
                    "extraction_id": result.extraction_id,
                    "vault_document_id": result.vault_document_id,
                    "status": result.status,
                    "text_length": result.text_length,
                    "quality_score": result.quality_score,
                    "requires_ocr": result.requires_ocr,
                },
            )
        except DocumentNotFoundError as exc:
            raise PermanentJobError(exc.message) from None
        except DocumentValidationError as exc:
            raise PermanentJobError(exc.message) from None
        except Exception as exc:
            if "Stockage" in str(exc) or "storage" in str(exc).lower():
                raise RetryableJobError(str(exc)[:200]) from None
            raise
        finally:
            if own:
                db.close()


class DocumentOCRJobHandler(JobHandler):
    """Préparé — OCR désactivé en V1 → blocked permanent (pas de simulation)."""

    handler_name = "vault_document_ocr_v1"
    job_name = JobNames.VAULT_DOCUMENT_OCR

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        from app.config import settings

        context.update_progress(10, "checking_ocr_provider")
        if not settings.elfis_ocr_enabled or (settings.elfis_ocr_provider or "").lower() == "disabled":
            raise PermanentJobError("OCR non configuré (ELFIS_OCR_PROVIDER=disabled)")
        raise PermanentJobError("Provider OCR non implémenté en V1")


class DocumentPrepareAnalysisJobHandler(JobHandler):
    """Préparé — en V1 l'enchaînement se fait via Event Bus."""

    handler_name = "vault_document_prepare_analysis_v1"
    job_name = JobNames.VAULT_DOCUMENT_PREPARE_ANALYSIS

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        return JobExecutionResult(
            status="completed",
            progress=100,
            message="prepare_analysis_noop_v1",
            result={
                "vault_document_id": payload.get("vault_document_id"),
                "extraction_id": payload.get("extraction_id"),
                "status": "ready",
            },
        )
