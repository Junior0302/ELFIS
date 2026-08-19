"""Handler Job Queue — Document Extraction Engine V1."""

from __future__ import annotations

from app.document_extraction.exceptions import (
    DocumentExtractionError,
    DocumentExtractionIneligibleError,
    DocumentExtractionNotFoundError,
)
from app.document_extraction.service import DocumentExtractionService
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


class DocumentExtractionRunJobHandler(JobHandler):
    handler_name = "document_extraction_run_v1"
    job_name = JobNames.DOCUMENT_EXTRACTION_RUN

    def handle(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        payload = job.payload if isinstance(job.payload, dict) else {}
        extraction_id = str(payload.get("extraction_id") or "").strip()
        if not extraction_id:
            raise PermanentJobError("extraction_id requis")
        org_id = int(job.organization_id or payload.get("organization_id") or 0)
        if not org_id:
            raise PermanentJobError("organization_id requis")

        context.update_progress(10, "loading_extraction")
        db, own = _session(context)
        try:
            svc = DocumentExtractionService(db)
            row = svc._run(
                extraction_id,
                org_id,
                actor_user_id=job.user_id,
            )
            context.update_progress(100, "completed")
            return JobExecutionResult(
                status="completed",
                result={
                    "extraction_id": row.id,
                    "status": row.status,
                    "overall_confidence": row.overall_confidence,
                },
            )
        except DocumentExtractionNotFoundError as exc:
            raise PermanentJobError(str(exc.message)) from exc
        except DocumentExtractionIneligibleError as exc:
            raise PermanentJobError(str(exc.message)) from exc
        except DocumentExtractionError as exc:
            raise RetryableJobError(str(exc.message)) from exc
        except Exception as exc:
            raise RetryableJobError(type(exc).__name__) from exc
        finally:
            if own:
                db.close()
