"""Worker Job Queue — exécution hors processus HTTP."""

from __future__ import annotations

import json
import logging
import os
import random
import socket
import time
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.jobs.job_context import JobContext
from app.jobs.job_exceptions import PermanentJobError, RetryableJobError
from app.jobs.job_logging import sanitize_job_error, safe_job_log_context
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandlerRegistry, default_job_registry
from app.jobs.job_repository import JobRepository
from app.jobs.job_schemas import JobExecutionResult
from app.jobs.job_types import AttemptStatus, JobStatus

logger = logging.getLogger(__name__)


def compute_job_retry_delay_seconds(
    attempt_count: int,
    *,
    base_seconds: int | None = None,
    jitter: bool = True,
    jitter_seed: float | None = None,
) -> int:
    """
    Backoff : 15, 45, 135, 405, 1215… plafond 1 h.
    attempt_count = numéro de la tentative qui vient d'échouer (1-based).
    """
    base = base_seconds if base_seconds is not None else settings.elfis_job_retry_base_seconds
    base = max(1, base)
    exp = max(0, attempt_count - 1)
    delay = base * (3**exp)
    delay = min(delay, 3600)
    if jitter:
        factor = jitter_seed if jitter_seed is not None else (0.85 + random.random() * 0.3)
        delay = int(delay * factor)
    return max(base, delay)


def default_job_worker_id() -> str:
    configured = (settings.elfis_job_worker_id or "").strip()
    if configured:
        return configured[:128]
    return f"job-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def parse_queues(raw: str | None = None) -> list[str]:
    value = raw if raw is not None else settings.elfis_job_worker_queues
    parts = [p.strip() for p in (value or "default").split(",") if p.strip()]
    return parts or ["default"]


def _lifecycle_payload(job: ElfisJob) -> dict:
    return {
        "job_id": job.job_id,
        "job_name": job.job_name,
        "organization_id": job.organization_id,
        "queue_name": job.queue_name,
        "status": job.status,
        "attempt_count": job.attempt_count,
        "progress": job.progress,
        "correlation_id": job.correlation_id,
    }


def _publish(event_name: str, job: ElfisJob, db: Session) -> None:
    corr = None
    if job.correlation_id:
        try:
            corr = uuid.UUID(str(job.correlation_id))
        except (TypeError, ValueError):
            corr = None
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=job.organization_id if job.organization_id is not None else 0,
            aggregate_type="job",
            aggregate_id=job.job_id,
            payload=_lifecycle_payload(job),
            metadata={"source": "job_worker"},
            correlation_id=corr or uuid.uuid4(),
        ),
    )


def _result_size_ok(result: dict | None) -> bool:
    if result is None:
        return True
    size = len(json.dumps(result, ensure_ascii=False, default=str).encode("utf-8"))
    return size <= max(256, int(settings.elfis_job_max_result_bytes))


class JobWorker:
    """
    Timeout V1 : pas d'interruption de thread dangereuse.
    Après exécution du handler synchrone, si duration > timeout_seconds,
    le résultat est traité comme timed_out (retry / dead_letter).
    Un heartbeat périodique peut être appelé par le handler via context.heartbeat().
    """

    def __init__(
        self,
        db: Session,
        *,
        registry: JobHandlerRegistry | None = None,
        worker_id: str | None = None,
        queues: list[str] | None = None,
        batch_size: int | None = None,
        lock_timeout_seconds: int | None = None,
        session_factory=None,
    ):
        self._db = db
        self._registry = registry or default_job_registry
        self._repo = JobRepository(db)
        self.worker_id = worker_id or default_job_worker_id()
        self.queues = queues or parse_queues()
        self.batch_size = batch_size or settings.elfis_job_worker_batch_size
        self.lock_timeout_seconds = (
            lock_timeout_seconds or settings.elfis_job_lock_timeout_seconds
        )
        self._session_factory = session_factory or SessionLocal

    def reserve_next_batch(self) -> list[ElfisJob]:
        return self._repo.claim_jobs(
            worker_id=self.worker_id,
            queues=self.queues,
            batch_size=self.batch_size,
            lock_timeout_seconds=self.lock_timeout_seconds,
        )

    def process_next_batch(self) -> int:
        claimed = self.reserve_next_batch()
        processed = 0
        for job in claimed:
            self.process_job(job.job_id)
            processed += 1
        return processed

    def recover_stale_jobs(self) -> int:
        """Récupération explicite via claim (locks expirés inclus)."""
        return len(self.reserve_next_batch())

    def process_job(self, job_id: str) -> None:
        job = self._repo.find_by_job_id(job_id)
        if not job:
            return
        if job.status == JobStatus.COMPLETED:
            logger.info("job_skip_completed", extra=safe_job_log_context(job))
            return
        if job.status != JobStatus.PROCESSING:
            return

        _publish(EventNames.JOB_STARTED, job, self._db)
        logger.info("job_started", extra=safe_job_log_context(job, worker_id=self.worker_id))

        attempt = self._repo.find_attempt(job.job_id, job.attempt_count)
        context = JobContext(
            job_id=job.job_id,
            organization_id=job.organization_id,
            user_id=job.user_id,
            correlation_id=job.correlation_id,
            attempt_number=job.attempt_count,
            worker_id=self.worker_id,
            session_factory=self._session_factory,
        )

        started = time.monotonic()
        timeout = job.timeout_seconds or settings.elfis_job_default_timeout_seconds
        try:
            exec_result = self.execute_handler(job, context)
            duration_ms = int((time.monotonic() - started) * 1000)
            if duration_ms > timeout * 1000:
                self.mark_timed_out(job, attempt, duration_ms=duration_ms, reason="handler_exceeded_timeout")
                return
            self.complete_job(job, attempt, exec_result, duration_ms=duration_ms)
        except RetryableJobError as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.schedule_retry(job, attempt, error=exc, duration_ms=duration_ms)
        except PermanentJobError as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.mark_failed(job, attempt, error=exc, duration_ms=duration_ms, permanent=True)
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.schedule_retry(job, attempt, error=exc, duration_ms=duration_ms)

    def execute_handler(self, job: ElfisJob, context: JobContext) -> JobExecutionResult:
        handler = self._registry.get(job.job_name)
        result = handler.handle(job, context)
        if result is None:
            return JobExecutionResult(status="completed", result={"ok": True}, progress=100)
        if isinstance(result, JobExecutionResult):
            return result
        return JobExecutionResult(status="completed", result=dict(result), progress=100)

    def complete_job(
        self,
        job: ElfisJob,
        attempt,
        exec_result: JobExecutionResult,
        *,
        duration_ms: int,
    ) -> None:
        now = datetime.utcnow()
        result = exec_result.result if isinstance(exec_result.result, dict) else None
        if result is not None and not _result_size_ok(result):
            result = {"truncated": True, "message": "result trop volumineux"}
        from app.jobs.job_logging import assert_safe_payload

        try:
            assert_safe_payload(result, label="result")
        except Exception:
            result = {"ok": True, "sanitized": True}

        job.status = JobStatus.COMPLETED
        job.progress = max(0, min(100, int(exec_result.progress if exec_result.progress is not None else 100)))
        job.progress_message = (exec_result.message or "")[:255] or None
        job.result = result
        job.completed_at = now
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None
        job.last_error = None
        job.updated_at = now
        self._repo.save_job(job)

        if attempt:
            attempt.status = AttemptStatus.COMPLETED
            attempt.completed_at = now
            attempt.duration_ms = duration_ms
            attempt.error_type = None
            attempt.error_message = None
            self._repo.save_attempt(attempt)

        _publish(EventNames.JOB_COMPLETED, job, self._db)
        logger.info(
            "job_completed",
            extra=safe_job_log_context(job, duration_ms=duration_ms, worker_id=self.worker_id),
        )

    def schedule_retry(
        self,
        job: ElfisJob,
        attempt,
        *,
        error: Exception,
        duration_ms: int,
    ) -> None:
        now = datetime.utcnow()
        err_msg = sanitize_job_error(getattr(error, "message", None) or str(error))
        err_type = type(error).__name__

        if attempt:
            attempt.status = AttemptStatus.FAILED
            attempt.failed_at = now
            attempt.duration_ms = duration_ms
            attempt.error_type = err_type
            attempt.error_message = err_msg
            self._repo.save_attempt(attempt)

        if job.attempt_count >= job.max_attempts:
            self.mark_dead_letter(job, error_message=err_msg, error_type=err_type)
            return

        delay = compute_job_retry_delay_seconds(job.attempt_count)
        job.status = JobStatus.RETRY
        job.available_at = now + timedelta(seconds=delay)
        job.last_error = err_msg
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None
        job.failed_at = None
        job.updated_at = now
        self._repo.save_job(job)
        _publish(EventNames.JOB_RETRY_SCHEDULED, job, self._db)
        logger.warning(
            "job_retry_scheduled",
            extra=safe_job_log_context(
                job,
                duration_ms=duration_ms,
                retry_delay_seconds=delay,
                error_type=err_type,
            ),
        )

    def mark_failed(
        self,
        job: ElfisJob,
        attempt,
        *,
        error: Exception,
        duration_ms: int,
        permanent: bool = False,
    ) -> None:
        now = datetime.utcnow()
        err_msg = sanitize_job_error(getattr(error, "message", None) or str(error))
        err_type = type(error).__name__

        if attempt:
            attempt.status = AttemptStatus.FAILED
            attempt.failed_at = now
            attempt.duration_ms = duration_ms
            attempt.error_type = err_type
            attempt.error_message = err_msg
            self._repo.save_attempt(attempt)

        # PermanentJobError → failed (pas de retry). dead_letter si max déjà atteint.
        if permanent and job.attempt_count < job.max_attempts:
            job.status = JobStatus.FAILED
            job.failed_at = now
            job.last_error = err_msg
            job.locked_at = None
            job.locked_by = None
            job.heartbeat_at = None
            job.updated_at = now
            self._repo.save_job(job)
            _publish(EventNames.JOB_FAILED, job, self._db)
            logger.error(
                "job_failed_permanent",
                extra=safe_job_log_context(job, duration_ms=duration_ms, error_type=err_type),
            )
            return
        self.mark_dead_letter(job, error_message=err_msg, error_type=err_type)

    def mark_dead_letter(
        self,
        job: ElfisJob,
        *,
        error_message: str | None,
        error_type: str | None = None,
    ) -> None:
        now = datetime.utcnow()
        job.status = JobStatus.DEAD_LETTER
        job.failed_at = now
        job.last_error = sanitize_job_error(error_message)
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None
        job.updated_at = now
        self._repo.save_job(job)
        _publish(EventNames.JOB_DEAD_LETTERED, job, self._db)
        logger.error(
            "job_dead_lettered",
            extra=safe_job_log_context(job, error_type=error_type),
        )

    def mark_timed_out(self, job: ElfisJob, attempt, *, duration_ms: int, reason: str) -> None:
        now = datetime.utcnow()
        err_msg = sanitize_job_error(f"timeout: {reason}")
        if attempt:
            attempt.status = AttemptStatus.TIMED_OUT
            attempt.failed_at = now
            attempt.duration_ms = duration_ms
            attempt.error_type = "Timeout"
            attempt.error_message = err_msg
            self._repo.save_attempt(attempt)

        _publish(EventNames.JOB_TIMED_OUT, job, self._db)

        if job.attempt_count >= job.max_attempts:
            self.mark_dead_letter(job, error_message=err_msg, error_type="Timeout")
            return

        delay = compute_job_retry_delay_seconds(job.attempt_count)
        job.status = JobStatus.RETRY
        job.available_at = now + timedelta(seconds=delay)
        job.last_error = err_msg
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None
        job.updated_at = now
        self._repo.save_job(job)
        _publish(EventNames.JOB_RETRY_SCHEDULED, job, self._db)
        logger.warning(
            "job_timed_out",
            extra=safe_job_log_context(job, duration_ms=duration_ms, retry_delay_seconds=delay),
        )


def run_worker_loop(*, once: bool = False) -> None:
    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()
    worker_id = default_job_worker_id()
    queues = parse_queues()
    poll = settings.elfis_job_worker_poll_interval_seconds
    logger.info(
        "job_worker_start",
        extra={"worker_id": worker_id, "queues": queues, "poll_interval": poll},
    )
    while True:
        session = SessionLocal()
        try:
            JobWorker(session, worker_id=worker_id, queues=queues).process_next_batch()
        except Exception:
            logger.exception("job_worker_batch_error", extra={"worker_id": worker_id})
        finally:
            session.close()
        if once:
            break
        time.sleep(poll)


if __name__ == "__main__":
    run_worker_loop()
