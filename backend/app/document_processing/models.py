"""Modèles SQLAlchemy — Document Processing Jobs."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisDocumentProcessingJob(Base):
    __tablename__ = "elfis_document_processing_jobs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_elfis_dp_jobs_org_idempotency",
        ),
        Index("ix_elfis_dp_jobs_status_scheduled", "status", "scheduled_at"),
        Index("ix_elfis_dp_jobs_org_created", "organization_id", "created_at"),
        Index("ix_elfis_dp_jobs_document_created", "document_id", "created_at"),
        Index("ix_elfis_dp_jobs_version", "document_version_id"),
        Index("ix_elfis_dp_jobs_pipeline_status", "pipeline_key", "status"),
        Index("ix_elfis_dp_jobs_locked_until", "locked_until"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    document_version_id = Column(String(36), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    product = Column(String(64), nullable=True)
    pipeline_key = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=100)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    idempotency_key = Column(String(255), nullable=True)
    correlation_id = Column(String(36), nullable=True)
    request_id = Column(String(64), nullable=True)
    progress_percent = Column(Integer, nullable=False, default=0)
    current_step_key = Column(String(64), nullable=True)
    attempts_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    scheduled_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message_sanitized = Column(String(255), nullable=True)
    result_summary_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    locked_at = Column(DateTime, nullable=True)
    locked_until = Column(DateTime, nullable=True)
    locked_by = Column(String(128), nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    cancellation_requested_at = Column(DateTime, nullable=True)
    cancellation_requested_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentProcessingStep(Base):
    __tablename__ = "elfis_document_processing_steps"
    __table_args__ = (
        UniqueConstraint("job_id", "step_key", name="uq_elfis_dp_steps_job_key"),
        UniqueConstraint("job_id", "sequence_number", name="uq_elfis_dp_steps_job_seq"),
        Index("ix_elfis_dp_steps_next_retry", "next_retry_at"),
        Index("ix_elfis_dp_steps_job_seq", "job_id", "sequence_number"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    job_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key = Column(String(64), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    required = Column(Boolean, nullable=False, default=True)
    attempts_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    timeout_seconds = Column(Integer, nullable=False, default=120)
    last_error_code = Column(String(64), nullable=True)
    last_error_message_sanitized = Column(String(255), nullable=True)
    input_summary_json = Column(JSON, nullable=True)
    output_summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentProcessingAttempt(Base):
    __tablename__ = "elfis_document_processing_attempts"
    __table_args__ = (
        UniqueConstraint("step_id", "attempt_number", name="uq_elfis_dp_attempts_step_num"),
        Index("ix_elfis_dp_attempts_job", "job_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    job_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_steps.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(128), nullable=False, default="")
    status = Column(String(32), nullable=False, default="running")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message_sanitized = Column(String(255), nullable=True)
    retryable = Column(Boolean, nullable=False, default=False)
    metadata_json = Column(JSON, nullable=True)
