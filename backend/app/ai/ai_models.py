"""Modèles SQLAlchemy — ELFIS AI Engine."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
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


class ElfisAIExecution(Base):
    __tablename__ = "elfis_ai_executions"
    __table_args__ = (
        UniqueConstraint("execution_id", name="uq_elfis_ai_executions_execution_id"),
        CheckConstraint(
            "status IN ("
            "'pending','processing','completed','failed',"
            "'cancelled','blocked','requires_review'"
            ")",
            name="ck_elfis_ai_executions_status",
        ),
        Index("ix_elfis_ai_executions_input_ref", "input_reference_type", "input_reference_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    execution_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    task_name = Column(String(128), nullable=False, index=True)
    task_version = Column(Integer, nullable=False, default=1)

    provider = Column(String(64), nullable=False, index=True)
    model = Column(String(128), nullable=False, index=True)

    status = Column(String(32), nullable=False, index=True)

    input_reference_type = Column(String(64), nullable=True)
    input_reference_id = Column(String(128), nullable=True)
    input_hash = Column(String(64), nullable=True)

    result = Column(JSON, nullable=True)
    result_schema_version = Column(Integer, nullable=True)
    prompt_version = Column(String(64), nullable=True)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    estimated_cost = Column(Numeric(14, 6), nullable=True)
    currency = Column(String(8), nullable=False, default="USD")

    latency_ms = Column(Integer, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)

    job_id = Column(String(36), nullable=True, index=True)
    correlation_id = Column(String(36), nullable=True, index=True)
    source_event_id = Column(String(36), nullable=True)

    idempotency_key = Column(String(255), nullable=True, index=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ElfisAIUsage(Base):
    __tablename__ = "elfis_ai_usage"
    __table_args__ = (
        Index("ix_elfis_ai_usage_organization_id", "organization_id"),
        Index("ix_elfis_ai_usage_request_date", "request_date"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    execution_id = Column(
        String(36), ForeignKey("elfis_ai_executions.execution_id"), nullable=False, index=True
    )

    provider = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    task_name = Column(String(128), nullable=False, index=True)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    estimated_cost = Column(Numeric(14, 6), nullable=True)
    currency = Column(String(8), nullable=False, default="USD")

    request_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ElfisDocumentAnalysis(Base):
    __tablename__ = "elfis_document_analyses"
    __table_args__ = (
        UniqueConstraint("analysis_id", name="uq_elfis_document_analyses_analysis_id"),
        UniqueConstraint(
            "organization_id",
            "vault_document_id",
            "document_version",
            name="uq_elfis_document_analyses_org_doc_ver",
        ),
        CheckConstraint(
            "status IN ("
            "'pending','classifying','extracting','validating',"
            "'completed','failed','requires_review','blocked'"
            ")",
            name="ck_elfis_document_analyses_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    vault_document_id = Column(String(36), nullable=False, index=True)
    document_version = Column(Integer, nullable=False, default=1)

    document_type = Column(String(64), nullable=True)
    classification = Column(JSON, nullable=True)
    extraction = Column(JSON, nullable=True)
    quality = Column(JSON, nullable=True)
    accounting_mapping = Column(JSON, nullable=True)

    status = Column(String(32), nullable=False, index=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    requires_review = Column(Boolean, nullable=False, default=False)
    current_stage = Column(String(64), nullable=True)

    ai_execution_ids = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
