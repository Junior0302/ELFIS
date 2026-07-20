"""Service métier Job Queue."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.jobs.job_exceptions import (
    JobNotFoundError,
    JobUnknownTypeError,
    JobValidationError,
)
from app.jobs.job_logging import assert_safe_payload, safe_job_log_context
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandlerRegistry, default_job_registry
from app.jobs.job_repository import JobRepository
from app.jobs.job_schemas import JobRequest, JobResult, JobUserView
from app.jobs.job_types import DEFAULT_QUEUE, IMPLEMENTED_JOB_NAMES, JobStatus

logger = logging.getLogger(__name__)

CANCELABLE = frozenset({JobStatus.PENDING, JobStatus.SCHEDULED, JobStatus.RETRY})
MANUAL_RETRYABLE = frozenset({JobStatus.FAILED, JobStatus.DEAD_LETTER})


def _payload_size_bytes(data: dict[str, Any]) -> int:
    return len(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))


def _job_lifecycle_payload(job: ElfisJob) -> dict[str, Any]:
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


def _as_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _publish_job_event(event_name: str, job: ElfisJob, *, db: Session) -> None:
    corr = _as_uuid(job.correlation_id) or uuid.uuid4()
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=job.organization_id if job.organization_id is not None else 0,
            aggregate_type="job",
            aggregate_id=job.job_id,
            payload=_job_lifecycle_payload(job),
            metadata={"source": "job_service"},
            correlation_id=corr,
            causation_id=_as_uuid(job.causation_event_id),
        ),
    )


class JobService:
    def __init__(
        self,
        db: Session,
        *,
        registry: JobHandlerRegistry | None = None,
    ):
        self._db = db
        self._repo = JobRepository(db)
        self._registry = registry or default_job_registry

    def enqueue(self, request: JobRequest) -> JobResult:
        job_name = (request.job_name or "").strip()
        if not job_name:
            raise JobValidationError("job_name requis")
        if not self._registry.is_known(job_name):
            raise JobUnknownTypeError(job_name)
        if job_name not in IMPLEMENTED_JOB_NAMES:
            raise JobUnknownTypeError(job_name)
        if not self._registry.has(job_name):
            raise JobUnknownTypeError(job_name)

        queue_name = (request.queue_name or DEFAULT_QUEUE).strip() or DEFAULT_QUEUE
        if len(queue_name) > 64:
            raise JobValidationError("queue_name trop long")

        payload = dict(request.payload or {})
        assert_safe_payload(payload, label="payload")
        max_bytes = max(256, int(settings.elfis_job_max_payload_bytes))
        if _payload_size_bytes(payload) > max_bytes:
            raise JobValidationError(f"payload trop volumineux (max {max_bytes} octets)")

        idem = (request.idempotency_key or "").strip() or None
        if idem:
            existing = self._repo.find_by_idempotency_key(idem)
            if existing:
                logger.info(
                    "job_enqueue_idempotent_reuse",
                    extra=safe_job_log_context(existing),
                )
                return JobResult(
                    job_id=existing.job_id,
                    created=False,
                    status=existing.status,
                    queue_name=existing.queue_name,
                    scheduled_at=existing.scheduled_at,
                    idempotent_reuse=True,
                )

        now = datetime.utcnow()
        scheduled_at = request.scheduled_at
        if scheduled_at is not None and scheduled_at.tzinfo is not None:
            scheduled_at = scheduled_at.replace(tzinfo=None)

        if scheduled_at and scheduled_at > now:
            status = JobStatus.SCHEDULED
            available_at = scheduled_at
        else:
            status = JobStatus.PENDING
            available_at = now
            scheduled_at = scheduled_at if scheduled_at else None

        max_attempts = max(1, min(50, int(request.max_attempts or settings.elfis_job_max_attempts)))
        priority = int(request.priority if request.priority is not None else 100)
        timeout = request.timeout_seconds
        if timeout is None:
            timeout = settings.elfis_job_default_timeout_seconds
        timeout = max(1, min(86400, int(timeout)))

        job = ElfisJob(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            organization_id=request.organization_id,
            user_id=request.user_id,
            job_name=job_name,
            job_version=max(1, int(request.job_version or 1)),
            queue_name=queue_name,
            payload=payload,
            result=None,
            status=status,
            priority=priority,
            progress=0,
            progress_message=None,
            attempt_count=0,
            max_attempts=max_attempts,
            available_at=available_at,
            scheduled_at=scheduled_at,
            timeout_seconds=timeout,
            idempotency_key=idem,
            correlation_id=str(request.correlation_id) if request.correlation_id else str(uuid.uuid4()),
            causation_event_id=str(request.causation_event_id) if request.causation_event_id else None,
            parent_job_id=str(request.parent_job_id) if request.parent_job_id else None,
            created_at=now,
            updated_at=now,
        )
        try:
            self._repo.create_job(job)
        except Exception as exc:
            if idem:
                again = self._repo.find_by_idempotency_key(idem)
                if again:
                    return JobResult(
                        job_id=again.job_id,
                        created=False,
                        status=again.status,
                        queue_name=again.queue_name,
                        scheduled_at=again.scheduled_at,
                        idempotent_reuse=True,
                    )
            raise JobValidationError("Échec de création du job") from exc

        _publish_job_event(EventNames.JOB_CREATED, job, db=self._db)
        logger.info("job_created", extra=safe_job_log_context(job))
        return JobResult(
            job_id=job.job_id,
            created=True,
            status=job.status,
            queue_name=job.queue_name,
            scheduled_at=job.scheduled_at,
            idempotent_reuse=False,
        )

    def enqueue_many(self, requests: list[JobRequest]) -> list[JobResult]:
        return [self.enqueue(r) for r in requests]

    def get_job(self, job_id: str) -> ElfisJob:
        job = self._repo.find_by_job_id(job_id)
        if not job:
            raise JobNotFoundError()
        return job

    def list_jobs(self, **kwargs: Any) -> tuple[list[ElfisJob], int]:
        return self._repo.list_jobs(**kwargs)

    def get_job_attempts(self, job_id: str):
        self.get_job(job_id)
        return self._repo.list_attempts(job_id)

    def cancel_job(self, job_id: str, *, actor_user_id: int | None = None) -> ElfisJob:
        job = self.get_job(job_id)
        if job.status not in CANCELABLE:
            raise JobValidationError(
                f"Annulation refusée pour le statut {job.status} (V1: pending/scheduled/retry uniquement)"
            )
        now = datetime.utcnow()
        job.status = JobStatus.CANCELLED
        job.cancelled_at = now
        job.updated_at = now
        self._repo.save_job(job)
        _publish_job_event(EventNames.JOB_CANCELLED, job, db=self._db)
        logger.info(
            "job_cancelled",
            extra=safe_job_log_context(job, actor_user_id=actor_user_id),
        )
        return job

    def retry_job(self, job_id: str, *, actor_user_id: int | None = None) -> ElfisJob:
        """
        Retry manuel plateforme.

        Stratégie V1 :
        - historique elfis_job_attempts conservé ;
        - attempt_count remis à 0 (nouveau cycle de max_attempts) ;
        - statut pending, available_at = now ;
        - locks / erreurs nettoyés.
        """
        job = self.get_job(job_id)
        if job.status not in MANUAL_RETRYABLE:
            raise JobValidationError(
                f"Retry manuel réservé aux jobs failed/dead_letter (actuel: {job.status})"
            )
        now = datetime.utcnow()
        job.status = JobStatus.PENDING
        job.attempt_count = 0
        job.available_at = now
        job.scheduled_at = None
        job.locked_at = None
        job.locked_by = None
        job.heartbeat_at = None
        job.started_at = None
        job.completed_at = None
        job.failed_at = None
        job.cancelled_at = None
        job.last_error = None
        job.progress = 0
        job.progress_message = None
        job.result = None
        job.updated_at = now
        self._repo.save_job(job)
        _publish_job_event(EventNames.JOB_RETRIED, job, db=self._db)
        logger.info(
            "job_retried_manual",
            extra=safe_job_log_context(job, actor_user_id=actor_user_id),
        )
        return job

    def to_user_view(self, job: ElfisJob) -> JobUserView:
        return JobUserView(
            job_id=job.job_id,
            job_name=job.job_name,
            status=job.status,
            progress=job.progress,
            progress_message=job.progress_message,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            failed_at=job.failed_at,
        )

    def user_can_access(self, job: ElfisJob, *, organization_id: int, user_id: int) -> bool:
        if job.organization_id is not None and job.organization_id != organization_id:
            return False
        if job.user_id is not None and job.user_id == user_id:
            return True
        if job.user_id is None and job.organization_id == organization_id:
            return True
        return False

    def filter_sensitive_dict(self, data: dict[str, Any] | None) -> dict[str, Any]:
        from app.jobs.job_logging import FORBIDDEN_PAYLOAD_KEYS

        if not data:
            return {}
        out: dict[str, Any] = {}
        for k, v in data.items():
            lk = str(k).lower()
            if lk in FORBIDDEN_PAYLOAD_KEYS:
                continue
            if any(x in lk for x in ("password", "secret", "token", "api_key", "jwt")):
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                out[k] = v
            elif isinstance(v, dict):
                out[k] = self.filter_sensitive_dict(v)
            elif isinstance(v, list) and len(v) <= 20:
                out[k] = v[:20]
        return out
