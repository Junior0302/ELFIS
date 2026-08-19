"""Orchestrateur — exécute les étapes d'un job réservé."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.context import ProcessingContext
from app.document_processing.exceptions import (
    ProcessingCancelledError,
    ProcessingPermanentError,
    ProcessingRetryableError,
    ProcessingTimeoutError,
)
from app.document_processing.models import ElfisDocumentProcessingAttempt
from app.document_processing.policies import ProcessingRetryPolicy
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.sanitization import sanitize_error_message, sanitize_processing_metadata
from app.document_processing.step_registry import DocumentProcessingPipelineRegistry, get_pipeline_registry
from app.document_processing.types import ProcessingAttemptStatus, ProcessingJobStatus, ProcessingStepStatus
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject

logger = logging.getLogger(__name__)


class DocumentProcessingOrchestrator:
    def __init__(
        self,
        db: Session,
        *,
        registry: DocumentProcessingPipelineRegistry | None = None,
        audit_logger: Any | None = None,
        retry_policy: ProcessingRetryPolicy | None = None,
    ) -> None:
        self._db = db
        self._repo = DocumentProcessingRepository(db)
        self._registry = registry or get_pipeline_registry()
        self._audit = audit_logger
        self._retry = retry_policy or ProcessingRetryPolicy.from_settings()
        self._lease = int(getattr(settings, "document_processing_lease_seconds", 60) or 60)

    async def run_job(self, job_id: str, *, worker_id: str) -> None:
        job = self._repo.get_job(job_id)
        if not job:
            return
        self._safe("record_document_processing_job_started", job=job, worker_id=worker_id)

        if job.timeout_at and job.timeout_at < datetime.utcnow():
            self._fail_job(job, code="job_timeout", message="Timeout global job", timed_out=True)
            return

        doc = self._db.get(ElfisDocumentRecord, job.document_id)
        ver = self._db.get(ElfisDocumentVersion, job.document_version_id)
        if not doc or not ver:
            self._fail_job(job, code="document_not_found", message="Document/version absent", retryable=False)
            return

        obj = None
        if ver.storage_object_id:
            obj = self._db.get(ElfisStorageObject, ver.storage_object_id)

        steps = self._repo.list_steps(job.id)
        total = len(steps) or 1
        completed = 0

        for step in steps:
            self._repo.heartbeat(job, lease_seconds=self._lease)
            self._db.refresh(job)

            if job.cancellation_requested_at:
                self._cancel_job(job)
                return

            if step.status in (
                ProcessingStepStatus.COMPLETED.value,
                ProcessingStepStatus.SKIPPED.value,
            ):
                completed += 1
                continue

            if step.status == ProcessingStepStatus.CANCELLED.value:
                continue

            if step.next_retry_at and step.next_retry_at > datetime.utcnow():
                job.status = ProcessingJobStatus.RETRYING.value
                job.scheduled_at = step.next_retry_at
                job.locked_at = None
                job.locked_by = None
                job.locked_until = None
                job.updated_at = datetime.utcnow()
                self._db.commit()
                return

            # run step
            result = await self._run_step(job, step, doc, ver, obj, worker_id=worker_id)
            if result == "retry_later":
                return
            if result == "failed":
                return
            if result == "cancelled":
                return
            if result == "blocked":
                job.status = ProcessingJobStatus.BLOCKED.value
                job.updated_at = datetime.utcnow()
                self._db.commit()
                return
            completed += 1
            job.progress_percent = min(100, int(100 * completed / total))
            job.current_step_key = step.step_key
            job.updated_at = datetime.utcnow()
            self._db.commit()

        job.progress_percent = 100
        job.status = ProcessingJobStatus.COMPLETED.value
        job.completed_at = datetime.utcnow()
        job.locked_at = None
        job.locked_by = None
        job.locked_until = None
        job.result_summary_json = sanitize_processing_metadata(
            {"completed_steps": completed, "pipeline_key": job.pipeline_key}
        )
        job.updated_at = datetime.utcnow()
        self._db.commit()
        self._safe("record_document_processing_job_completed", job=job)

    async def _run_step(
        self,
        job,
        step,
        doc,
        ver,
        obj,
        *,
        worker_id: str,
    ) -> str:
        step.status = ProcessingStepStatus.RUNNING.value
        step.started_at = step.started_at or datetime.utcnow()
        step.attempts_count += 1
        step.updated_at = datetime.utcnow()
        job.current_step_key = step.step_key
        job.attempts_count += 1
        self._db.commit()

        attempt = ElfisDocumentProcessingAttempt(
            id=str(uuid4()),
            job_id=job.id,
            step_id=step.id,
            attempt_number=step.attempts_count,
            worker_id=worker_id[:128],
            status=ProcessingAttemptStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )
        self._repo.create_attempt(attempt, commit=True)
        self._safe(
            "record_document_processing_step_started",
            job=job,
            step_key=step.step_key,
            attempt_number=step.attempts_count,
            worker_id=worker_id,
        )

        ctx = ProcessingContext(
            db=self._db,
            job=job,
            step=step,
            document=doc,
            version=ver,
            storage_object=obj,
            worker_id=worker_id,
            cancellation_requested=bool(job.cancellation_requested_at),
        )
        handler = self._registry.get_handler(step.step_key)
        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                handler.execute(ctx),
                timeout=max(1, int(step.timeout_seconds or 120)),
            )
        except asyncio.TimeoutError:
            return self._step_failed(
                job,
                step,
                attempt,
                code="timeout",
                message="Timeout étape",
                retryable=True,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except ProcessingCancelledError:
            self._cancel_job(job)
            return "cancelled"
        except ProcessingRetryableError as exc:
            return self._step_failed(
                job,
                step,
                attempt,
                code=exc.code,
                message=sanitize_error_message(exc.message),
                retryable=True,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except ProcessingPermanentError as exc:
            return self._step_failed(
                job,
                step,
                attempt,
                code=exc.code,
                message=sanitize_error_message(exc.message),
                retryable=False,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return self._step_failed(
                job,
                step,
                attempt,
                code=type(exc).__name__,
                message=sanitize_error_message(exc),
                retryable=False,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        duration = int((time.perf_counter() - started) * 1000)
        if result.status == "blocked" or (not result.success and result.status == "blocked"):
            attempt.status = ProcessingAttemptStatus.FAILED.value
            attempt.completed_at = datetime.utcnow()
            attempt.duration_ms = duration
            attempt.error_code = result.error_code
            attempt.error_message_sanitized = result.error_message_sanitized
            attempt.retryable = False
            step.status = ProcessingStepStatus.BLOCKED.value
            step.last_error_code = result.error_code
            step.last_error_message_sanitized = result.error_message_sanitized
            step.failed_at = datetime.utcnow()
            self._db.commit()
            return "blocked"

        if not result.success:
            return self._step_failed(
                job,
                step,
                attempt,
                code=result.error_code or "step_failed",
                message=result.error_message_sanitized or "Échec étape",
                retryable=result.retryable,
                duration_ms=duration,
            )

        attempt.status = ProcessingAttemptStatus.COMPLETED.value
        attempt.completed_at = datetime.utcnow()
        attempt.duration_ms = duration
        step.status = (
            ProcessingStepStatus.SKIPPED.value
            if result.status == "skipped"
            else ProcessingStepStatus.COMPLETED.value
        )
        step.completed_at = datetime.utcnow()
        step.output_summary_json = sanitize_processing_metadata(result.output_summary)
        step.updated_at = datetime.utcnow()
        self._db.commit()
        self._safe(
            "record_document_processing_step_completed",
            job=job,
            step_key=step.step_key,
            attempt_number=step.attempts_count,
            duration_ms=duration,
        )
        return "ok"

    def _step_failed(
        self,
        job,
        step,
        attempt,
        *,
        code: str,
        message: str,
        retryable: bool,
        duration_ms: int,
    ) -> str:
        attempt.status = (
            ProcessingAttemptStatus.TIMED_OUT.value
            if code == "timeout"
            else ProcessingAttemptStatus.FAILED.value
        )
        attempt.completed_at = datetime.utcnow()
        attempt.duration_ms = duration_ms
        attempt.error_code = code[:64]
        attempt.error_message_sanitized = message[:255]
        attempt.retryable = retryable and self._retry.is_retryable(code)

        step.last_error_code = code[:64]
        step.last_error_message_sanitized = message[:255]
        step.failed_at = datetime.utcnow()
        step.updated_at = datetime.utcnow()
        job.last_error_code = code[:64]
        job.last_error_message_sanitized = message[:255]

        can_retry = attempt.retryable and step.attempts_count < step.max_attempts
        if can_retry:
            delay = self._retry.delay_seconds(step.attempts_count)
            step.status = ProcessingStepStatus.RETRYING.value
            step.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            job.status = ProcessingJobStatus.RETRYING.value
            job.scheduled_at = step.next_retry_at
            job.locked_at = None
            job.locked_by = None
            job.locked_until = None
            self._db.commit()
            self._safe(
                "record_document_processing_step_retry_scheduled",
                job=job,
                step_key=step.step_key,
                attempt_number=step.attempts_count,
                error_code=code,
            )
            return "retry_later"

        step.status = (
            ProcessingStepStatus.TIMED_OUT.value
            if code == "timeout"
            else ProcessingStepStatus.FAILED.value
        )
        if not step.required:
            step.status = ProcessingStepStatus.SKIPPED.value
            self._db.commit()
            return "ok"

        self._fail_job(
            job,
            code=code,
            message=message,
            retryable=False,
            timed_out=(code == "timeout"),
        )
        self._safe(
            "record_document_processing_step_failed",
            job=job,
            step_key=step.step_key,
            attempt_number=step.attempts_count,
            error_code=code,
        )
        return "failed"

    def _fail_job(
        self,
        job,
        *,
        code: str,
        message: str,
        retryable: bool = False,
        timed_out: bool = False,
    ) -> None:
        job.status = (
            ProcessingJobStatus.TIMED_OUT.value if timed_out else ProcessingJobStatus.FAILED.value
        )
        job.failed_at = datetime.utcnow()
        job.last_error_code = code[:64]
        job.last_error_message_sanitized = message[:255]
        job.locked_at = None
        job.locked_by = None
        job.locked_until = None
        job.updated_at = datetime.utcnow()
        self._db.commit()
        self._safe("record_document_processing_job_failed", job=job, error_code=code)

    def _cancel_job(self, job) -> None:
        now = datetime.utcnow()
        job.status = ProcessingJobStatus.CANCELLED.value
        job.cancelled_at = now
        job.locked_at = None
        job.locked_by = None
        job.locked_until = None
        job.updated_at = now
        for step in self._repo.list_steps(job.id):
            if step.status in (
                ProcessingStepStatus.PENDING.value,
                ProcessingStepStatus.READY.value,
                ProcessingStepStatus.RUNNING.value,
                ProcessingStepStatus.RETRYING.value,
            ):
                step.status = ProcessingStepStatus.CANCELLED.value
                step.updated_at = now
        self._db.commit()
        self._safe("record_document_processing_job_cancelled", job=job)

    def _safe(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            job = kwargs.get("job")
            payload = {k: v for k, v in kwargs.items() if k != "job"}
            if job is not None:
                payload.setdefault("job_id", job.id)
                payload.setdefault("document_id", job.document_id)
                payload.setdefault("version_id", job.document_version_id)
                payload.setdefault("organization_id", job.organization_id)
                payload.setdefault("pipeline_key", job.pipeline_key)
            getattr(self._audit, method)(**payload)
        except Exception:
            logger.debug("orchestrator_audit_failed", exc_info=True)
