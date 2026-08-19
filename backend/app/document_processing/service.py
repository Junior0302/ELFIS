"""DocumentProcessingService — création, cancel, retry, list."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.exceptions import (
    ProcessingAccessDeniedError,
    ProcessingNotFoundError,
    ProcessingValidationError,
)
from app.document_processing.models import (
    ElfisDocumentProcessingJob,
    ElfisDocumentProcessingStep,
)
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.sanitization import sanitize_error_message, sanitize_processing_metadata
from app.document_processing.step_registry import get_pipeline_registry
from app.document_processing.types import (
    JOB_TRANSITIONS,
    PIPELINE_BASIC_V1,
    ProcessingJobStatus,
    ProcessingStepStatus,
)
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion
from app.storage.storage_types import DocumentStatus

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = DocumentProcessingRepository(db)
        self._audit = audit_logger
        self._registry = get_pipeline_registry()

    def create_job(
        self,
        *,
        organization_id: int,
        document_id: str,
        pipeline_key: str | None = None,
        document_version_id: str | None = None,
        product: str | None = None,
        priority: int = 100,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        requested_by_user_id: int | None = None,
        correlation_id: str | None = None,
    ) -> ElfisDocumentProcessingJob:
        if not getattr(settings, "document_processing_enabled", True):
            raise ProcessingValidationError("processing_disabled", "Document processing désactivé")

        pipe_key = (pipeline_key or getattr(settings, "document_processing_default_pipeline", None) or PIPELINE_BASIC_V1).strip()
        pipeline = self._registry.get_pipeline(pipe_key)

        if idempotency_key:
            existing = self._repo.get_by_idempotency(organization_id, idempotency_key[:255])
            if existing:
                return existing

        doc = self._db.get(ElfisDocumentRecord, document_id)
        if not doc or doc.organization_id != organization_id:
            raise ProcessingAccessDeniedError("document_access_denied", "Document introuvable")
        if doc.status == DocumentStatus.PURGED.value:
            raise ProcessingValidationError("document_purged", "Document purgé")

        version_id = document_version_id or doc.current_version_id
        if not version_id:
            raise ProcessingValidationError("version_required", "Aucune version documentaire")
        ver = self._db.get(ElfisDocumentVersion, version_id)
        if not ver or ver.document_id != doc.id:
            raise ProcessingNotFoundError("version_not_found", "Version introuvable")

        max_attempts = int(getattr(settings, "document_processing_max_attempts", 3) or 3)
        job_timeout = int(getattr(settings, "document_processing_job_timeout_seconds", 900) or 900)
        now = datetime.utcnow()
        job = ElfisDocumentProcessingJob(
            id=str(uuid4()),
            document_id=doc.id,
            document_version_id=ver.id,
            organization_id=organization_id,
            product=(product or doc.product or None),
            pipeline_key=pipe_key,
            status=ProcessingJobStatus.QUEUED.value,
            priority=max(1, min(int(priority), 1000)),
            requested_by_user_id=requested_by_user_id,
            idempotency_key=(idempotency_key or None) and idempotency_key[:255],
            correlation_id=correlation_id or str(uuid4()),
            progress_percent=0,
            max_attempts=max_attempts,
            scheduled_at=now,
            timeout_at=now + timedelta(seconds=job_timeout),
            metadata_json=sanitize_processing_metadata(metadata),
        )
        self._repo.create_job(job, commit=False)
        for step_def in pipeline.steps:
            step = ElfisDocumentProcessingStep(
                id=str(uuid4()),
                job_id=job.id,
                step_key=step_def.key,
                sequence_number=step_def.sequence,
                status=ProcessingStepStatus.PENDING.value
                if step_def.sequence > 1
                else ProcessingStepStatus.READY.value,
                required=step_def.required,
                max_attempts=step_def.max_attempts,
                timeout_seconds=step_def.timeout_seconds,
            )
            self._repo.create_step(step, commit=False)
        self._db.commit()
        self._db.refresh(job)
        self._safe_audit("record_document_processing_job_created", job=job)
        self._safe_audit("record_document_processing_job_queued", job=job)
        return job

    def get_job_for_org(self, job_id: str, organization_id: int) -> ElfisDocumentProcessingJob:
        job = self._repo.get_job(job_id)
        if not job or job.organization_id != organization_id:
            raise ProcessingAccessDeniedError("job_access_denied", "Job introuvable")
        return job

    def get_job_platform(self, job_id: str) -> ElfisDocumentProcessingJob:
        job = self._repo.get_job(job_id)
        if not job:
            raise ProcessingNotFoundError("job_not_found", "Job introuvable")
        return job

    def list_jobs(self, **kwargs):
        return self._repo.list_jobs(**kwargs)

    def list_steps(self, job_id: str):
        return self._repo.list_steps(job_id)

    def list_attempts(self, job_id: str):
        return self._repo.list_attempts(job_id)

    def request_cancel(
        self,
        job_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentProcessingJob:
        job = self.get_job_platform(job_id) if platform else self.get_job_for_org(job_id, organization_id)
        if job.status in (
            ProcessingJobStatus.COMPLETED.value,
            ProcessingJobStatus.CANCELLED.value,
            ProcessingJobStatus.FAILED.value,
        ):
            return job  # idempotent
        now = datetime.utcnow()
        if job.status in (ProcessingJobStatus.PENDING.value, ProcessingJobStatus.QUEUED.value, ProcessingJobStatus.RETRYING.value):
            self._assert_transition(job.status, ProcessingJobStatus.CANCELLED.value)
            job.status = ProcessingJobStatus.CANCELLED.value
            job.cancelled_at = now
            job.updated_at = now
            for step in self._repo.list_steps(job.id):
                if step.status in (
                    ProcessingStepStatus.PENDING.value,
                    ProcessingStepStatus.READY.value,
                    ProcessingStepStatus.RETRYING.value,
                ):
                    step.status = ProcessingStepStatus.CANCELLED.value
                    step.updated_at = now
            self._db.commit()
            self._safe_audit("record_document_processing_job_cancelled", job=job)
            return job

        # running → request cancel
        job.cancellation_requested_at = now
        job.cancellation_requested_by_user_id = actor_user_id
        job.updated_at = now
        self._db.commit()
        self._safe_audit("record_document_processing_job_cancel_requested", job=job)
        return job

    def request_retry(
        self,
        job_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentProcessingJob:
        job = self.get_job_platform(job_id) if platform else self.get_job_for_org(job_id, organization_id)
        if job.status not in (
            ProcessingJobStatus.FAILED.value,
            ProcessingJobStatus.TIMED_OUT.value,
            ProcessingJobStatus.PARTIALLY_COMPLETED.value,
        ):
            raise ProcessingValidationError("invalid_transition", "Retry non autorisé pour ce statut")
        doc = self._db.get(ElfisDocumentRecord, job.document_id)
        if not doc or doc.status == DocumentStatus.PURGED.value:
            raise ProcessingValidationError("document_purged", "Document non retryable")
        now = datetime.utcnow()
        job.status = ProcessingJobStatus.QUEUED.value
        job.scheduled_at = now
        job.failed_at = None
        job.last_error_code = None
        job.last_error_message_sanitized = None
        job.locked_at = None
        job.locked_by = None
        job.locked_until = None
        job.updated_at = now
        for step in self._repo.list_steps(job.id):
            if step.status in (
                ProcessingStepStatus.FAILED.value,
                ProcessingStepStatus.TIMED_OUT.value,
                ProcessingStepStatus.RETRYING.value,
            ):
                step.status = ProcessingStepStatus.READY.value
                step.next_retry_at = None
                step.updated_at = now
        self._db.commit()
        self._safe_audit("record_document_processing_job_retry_requested", job=job, actor_user_id=actor_user_id)
        return job

    def _assert_transition(self, current: str, target: str) -> None:
        allowed = JOB_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise ProcessingValidationError("invalid_transition", f"{current} → {target}")

    def _safe_audit(self, method: str, *, job: ElfisDocumentProcessingJob, **extra: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(
                job_id=job.id,
                document_id=job.document_id,
                version_id=job.document_version_id,
                organization_id=job.organization_id,
                pipeline_key=job.pipeline_key,
                **{k: v for k, v in extra.items() if v is not None},
            )
        except Exception:
            logger.debug("processing_audit_failed", extra={"method": method}, exc_info=True)
