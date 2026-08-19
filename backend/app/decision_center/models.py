"""Modèles Decision Center — item + tentatives d’exécution."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisDecisionItem(Base):
    __tablename__ = "elfis_decision_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "deduplication_key",
            name="uq_elfis_decision_org_dedupe",
        ),
        CheckConstraint(
            "status IN ('open','in_progress','resolved','dismissed','expired')",
            name="ck_elfis_decision_status",
        ),
        CheckConstraint(
            "severity IN ('info','low','medium','high','critical')",
            name="ck_elfis_decision_severity",
        ),
        CheckConstraint(
            "execution_status IN ('idle','pending','running','succeeded','failed','cancelled')",
            name="ck_elfis_decision_execution_status",
        ),
        Index("ix_elfis_decision_org_status", "organization_id", "status"),
        Index("ix_elfis_decision_org_severity", "organization_id", "severity"),
        Index("ix_elfis_decision_org_source", "organization_id", "source_type", "source_id"),
        Index("ix_elfis_decision_org_created", "organization_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    decision_type = Column(String(64), nullable=False, index=True)
    source_type = Column(String(64), nullable=False)
    source_id = Column(String(64), nullable=False)
    source_event_id = Column(String(64), nullable=True)

    status = Column(String(32), nullable=False, default="open", index=True)
    severity = Column(String(16), nullable=False, default="medium")
    confidence = Column(Numeric(5, 4), nullable=True)

    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False, default="")
    explanation = Column(Text, nullable=False, default="")

    recommended_action_type = Column(String(64), nullable=False, default="open_resource")
    recommended_action_path = Column(String(512), nullable=True)
    required_permission = Column(String(64), nullable=True)

    metadata_json = Column("metadata", JSON, nullable=True)
    deduplication_key = Column(String(255), nullable=False)

    created_by_rule = Column(String(128), nullable=False)
    rule_version = Column(String(32), nullable=False, default="1")

    # C1.16 — état d’exécution (ne remplace pas status)
    execution_status = Column(String(32), nullable=False, default="idle")
    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)
    execution_failed_at = Column(DateTime, nullable=True)
    last_execution_error_code = Column(String(64), nullable=True)
    last_execution_error_message = Column(String(512), nullable=True)
    last_action_type = Column(String(64), nullable=True)
    last_action_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    execution_attempts = Column(Integer, nullable=False, default=0)
    last_source_refresh_at = Column(DateTime, nullable=True)

    # C1.17 — reprise de travail (pas de bucket persistant)
    started_at = Column(DateTime, nullable=True)
    started_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_activity_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class ElfisDecisionExecutionAttempt(Base):
    __tablename__ = "elfis_decision_execution_attempts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "decision_id",
            "action_type",
            "idempotency_key",
            name="uq_elfis_decision_exec_idem",
        ),
        CheckConstraint(
            "status IN ('running','succeeded','failed','cancelled')",
            name="ck_elfis_decision_exec_status",
        ),
        Index("ix_elfis_decision_exec_decision", "decision_id", "started_at"),
        Index("ix_elfis_decision_exec_org_status", "organization_id", "status"),
        Index("ix_elfis_decision_exec_action", "organization_id", "action_type"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    decision_id = Column(
        String(36),
        ForeignKey("elfis_decision_items.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="running")
    request_id = Column(String(64), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(String(512), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
