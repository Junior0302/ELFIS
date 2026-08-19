"""Modèles SQLAlchemy — Assistant de Migration."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
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
from app.migration_center.enums import (
    EMPTY_PROFILE_ENVELOPE,
    MigrationSessionStatus,
    STEP_WELCOME,
)


def _uuid() -> str:
    return str(uuid4())


def _mig_token() -> str:
    return f"mig_{uuid4().hex}"


def _empty_profile() -> dict:
    return {"schema_version": 1, "data": {}}


class ElfisMigrationSession(Base):
    __tablename__ = "elfis_migration_sessions"
    __table_args__ = (
        Index("ix_elfis_mig_org_created", "organization_id", "created_at"),
        Index("ix_elfis_mig_org_status", "organization_id", "status"),
        Index("ix_elfis_mig_created_by", "created_by_user_id"),
        Index("ix_elfis_mig_last_activity", "last_activity_at"),
        Index("ix_elfis_mig_mode_status", "organization_id", "mode", "status"),
        Index("ix_elfis_mig_org_token", "organization_id", "migration_session_token"),
        UniqueConstraint("migration_session_token", name="uq_elfis_mig_session_token"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    migration_session_token = Column(String(64), nullable=False, default=_mig_token, unique=True)
    mode = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default=MigrationSessionStatus.DRAFT.value)
    current_step = Column(Integer, nullable=False, default=STEP_WELCOME)
    company_profile = Column(JSON, nullable=True)
    migration_profile = Column(JSON, nullable=False, default=_empty_profile)
    ai_profile = Column(JSON, nullable=False, default=_empty_profile)
    selected_sources = Column(JSON, nullable=True)
    configuration = Column(JSON, nullable=True)
    progress = Column(JSON, nullable=True)
    answers_metadata = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(255), nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message_sanitized = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisMigrationTimelineEntry(Base):
    __tablename__ = "elfis_migration_timeline_entries"
    __table_args__ = (
        UniqueConstraint("migration_session_id", "step_key", name="uq_elfis_mig_tl_session_step"),
        Index("ix_elfis_mig_tl_org", "organization_id"),
        Index("ix_elfis_mig_tl_session", "migration_session_id"),
        Index("ix_elfis_mig_tl_step", "step_key"),
        Index("ix_elfis_mig_tl_status", "status"),
        Index("ix_elfis_mig_tl_created", "created_at"),
        Index("ix_elfis_mig_tl_org_session", "organization_id", "migration_session_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(
        String(36), ForeignKey("elfis_migration_sessions.id"), nullable=False
    )
    step_key = Column(String(64), nullable=False)
    step_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisMigrationActivity(Base):
    __tablename__ = "elfis_migration_activities"
    __table_args__ = (
        Index("ix_elfis_mig_act_org", "organization_id"),
        Index("ix_elfis_mig_act_session", "migration_session_id"),
        Index("ix_elfis_mig_act_type", "activity_type"),
        Index("ix_elfis_mig_act_occurred", "occurred_at"),
        Index("ix_elfis_mig_act_org_session", "organization_id", "migration_session_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(
        String(36), ForeignKey("elfis_migration_sessions.id"), nullable=False
    )
    activity_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(16), nullable=False, default="info")
    actor_type = Column(String(16), nullable=False, default="system")
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisMigrationMemoryEntry(Base):
    __tablename__ = "elfis_migration_memory_entries"
    __table_args__ = (
        Index("ix_elfis_mig_mem_org", "organization_id"),
        Index("ix_elfis_mig_mem_session", "migration_session_id"),
        Index("ix_elfis_mig_mem_scope", "scope"),
        Index("ix_elfis_mig_mem_type", "memory_type"),
        Index("ix_elfis_mig_mem_key", "key_hash"),
        Index("ix_elfis_mig_mem_status", "status"),
        Index("ix_elfis_mig_mem_org_session", "organization_id", "migration_session_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(
        String(36), ForeignKey("elfis_migration_sessions.id"), nullable=False
    )
    scope = Column(String(32), nullable=False, default="session")
    memory_type = Column(String(64), nullable=False)
    key_hash = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=True)
    source = Column(String(32), nullable=False, default="system")
    status = Column(String(32), nullable=False, default="proposed")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Compat import — EMPTY_PROFILE_ENVELOPE utilisé ailleurs
__all__ = [
    "ElfisMigrationSession",
    "ElfisMigrationTimelineEntry",
    "ElfisMigrationActivity",
    "ElfisMigrationMemoryEntry",
    "EMPTY_PROFILE_ENVELOPE",
]
