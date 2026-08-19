"""Modèles SQLAlchemy — Smart Migration Engine."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base
from app.smart_migration.enums import BatchItemStatus, BatchStatus, SmartRunStatus


def _uuid() -> str:
    return str(uuid4())


class ElfisSmartMigrationRun(Base):
    __tablename__ = "elfis_smart_migration_runs"
    __table_args__ = (
        Index("ix_elfis_sm_run_org", "organization_id", "created_at"),
        Index("ix_elfis_sm_run_mig", "migration_session_id"),
        Index("ix_elfis_sm_run_status", "organization_id", "status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(String(36), nullable=False)
    status = Column(String(32), nullable=False, default=SmartRunStatus.PENDING.value)
    batch_size = Column(Integer, nullable=False, default=25)
    max_workers = Column(Integer, nullable=False, default=4)
    parallel = Column(Boolean, nullable=False, default=False)
    progress_percent = Column(Float, nullable=False, default=0.0)
    documents_total = Column(Integer, nullable=False, default=0)
    documents_completed = Column(Integer, nullable=False, default=0)
    documents_pending = Column(Integer, nullable=False, default=0)
    documents_failed = Column(Integer, nullable=False, default=0)
    documents_imported = Column(Integer, nullable=False, default=0)
    active_batches = Column(Integer, nullable=False, default=0)
    active_workers = Column(Integer, nullable=False, default=0)
    eta_seconds = Column(Float, nullable=True)
    throughput_per_min = Column(Float, nullable=False, default=0.0)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    actual_cost = Column(Float, nullable=False, default=0.0)
    metrics_json = Column("metrics", JSON, nullable=False, default=dict)
    config_json = Column("config", JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(64), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisSmartMigrationBatch(Base):
    __tablename__ = "elfis_smart_migration_batches"
    __table_args__ = (
        Index("ix_elfis_sm_batch_run", "smart_run_id"),
        Index("ix_elfis_sm_batch_mig", "migration_session_id"),
        Index("ix_elfis_sm_batch_status", "organization_id", "status"),
        UniqueConstraint("smart_run_id", "batch_index", name="uq_elfis_sm_batch_idx"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    smart_run_id = Column(
        String(36), ForeignKey("elfis_smart_migration_runs.id"), nullable=False
    )
    migration_session_id = Column(String(36), nullable=False)
    batch_index = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default=BatchStatus.PENDING.value)
    documents_count = Column(Integer, nullable=False, default=0)
    completed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    progress_percent = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisSmartMigrationBatchItem(Base):
    __tablename__ = "elfis_smart_migration_batch_items"
    __table_args__ = (
        Index("ix_elfis_sm_item_batch", "batch_id"),
        Index("ix_elfis_sm_item_doc", "document_intake_item_id"),
        UniqueConstraint("batch_id", "document_intake_item_id", name="uq_elfis_sm_item_doc"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    smart_run_id = Column(String(36), nullable=False)
    batch_id = Column(
        String(36), ForeignKey("elfis_smart_migration_batches.id"), nullable=False
    )
    document_intake_item_id = Column(String(36), nullable=False)
    universal_document_id = Column(String(32), nullable=True)
    status = Column(String(32), nullable=False, default=BatchItemStatus.PENDING.value)
    stage = Column(String(64), nullable=True)  # intake|analysis|extraction|validation|import
    attempts = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    result_json = Column("result", JSON, nullable=False, default=dict)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisSmartMigrationReport(Base):
    __tablename__ = "elfis_smart_migration_reports"
    __table_args__ = (
        Index("ix_elfis_sm_rep_run", "smart_run_id"),
        UniqueConstraint("smart_run_id", "version", name="uq_elfis_sm_rep_ver"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    smart_run_id = Column(String(36), nullable=False)
    migration_session_id = Column(String(36), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    format = Column(String(16), nullable=False, default="json")  # json|csv|pdf
    summary_json = Column("summary", JSON, nullable=False, default=dict)
    stats_json = Column("stats", JSON, nullable=False, default=dict)
    created_objects_json = Column("created_objects", JSON, nullable=False, default=list)
    linked_objects_json = Column("linked_objects", JSON, nullable=False, default=list)
    errors_json = Column("errors", JSON, nullable=False, default=list)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    duration_ms = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    actual_cost = Column(Float, nullable=False, default=0.0)
    body_json = Column("body", JSON, nullable=False, default=dict)
    body_csv = Column(Text, nullable=True)
    body_pdf = Column(Text, nullable=True)  # base64 or plain text pdf stub
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisSmartMigrationCleanupLog(Base):
    __tablename__ = "elfis_smart_migration_cleanup_log"
    __table_args__ = (Index("ix_elfis_sm_cleanup_org", "organization_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(String(36), nullable=True)
    action = Column(String(64), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    dry_run = Column(Boolean, nullable=False, default=True)
    affected_count = Column(Integer, nullable=False, default=0)
    detail_json = Column("detail", JSON, nullable=False, default=dict)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
