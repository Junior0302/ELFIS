"""Modèles SQLAlchemy — Job Queue (distinct des events)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
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


class ElfisJob(Base):
    __tablename__ = "elfis_jobs"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_elfis_jobs_job_id"),
        CheckConstraint(
            "status IN ("
            "'pending','scheduled','processing','retry',"
            "'completed','failed','dead_letter','cancelled'"
            ")",
            name="ck_elfis_jobs_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_elfis_jobs_progress"),
        Index(
            "ix_elfis_jobs_claim",
            "status",
            "queue_name",
            "available_at",
            "priority",
            "created_at",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    job_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    job_name = Column(String(128), nullable=False, index=True)
    job_version = Column(Integer, nullable=False, default=1)
    queue_name = Column(String(64), nullable=False, default="default", index=True)

    payload = Column(JSON, nullable=False, default=dict)
    result = Column(JSON, nullable=True)

    status = Column(String(32), nullable=False, index=True)
    priority = Column(Integer, nullable=False, default=100)

    progress = Column(Integer, nullable=False, default=0)
    progress_message = Column(String(255), nullable=True)

    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)

    available_at = Column(DateTime, nullable=False, index=True)
    scheduled_at = Column(DateTime, nullable=True)

    locked_at = Column(DateTime, nullable=True, index=True)
    locked_by = Column(String(128), nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    timeout_seconds = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)

    idempotency_key = Column(String(255), nullable=True, index=True)
    correlation_id = Column(String(36), nullable=True, index=True)
    causation_event_id = Column(String(36), nullable=True)
    parent_job_id = Column(String(36), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ElfisJobAttempt(Base):
    __tablename__ = "elfis_job_attempts"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_elfis_job_attempts_job_attempt"),
        CheckConstraint(
            "status IN ('processing','completed','failed','timed_out','cancelled')",
            name="ck_elfis_job_attempts_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    job_id = Column(String(36), ForeignKey("elfis_jobs.job_id"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, index=True)

    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    duration_ms = Column(Integer, nullable=True)
    error_type = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
