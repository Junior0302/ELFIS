"""Modèles SQLAlchemy — Document Extraction."""

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
from app.document_extraction.enums import ExtractionStatus


def _uuid() -> str:
    return str(uuid4())


class ElfisDocumentExtraction(Base):
    __tablename__ = "elfis_document_extractions"
    __table_args__ = (
        Index("ix_elfis_extr_org_created", "organization_id", "created_at"),
        Index("ix_elfis_extr_item", "document_intake_item_id"),
        Index("ix_elfis_extr_status", "organization_id", "status"),
        Index("ix_elfis_extr_fingerprint", "organization_id", "input_fingerprint"),
        Index("ix_elfis_extr_universal", "universal_document_id"),
        UniqueConstraint(
            "organization_id",
            "input_fingerprint",
            "status_scope",
            name="uq_elfis_extr_active_fingerprint",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(String(36), nullable=True)
    document_intake_item_id = Column(
        String(36), ForeignKey("elfis_document_intake_items.id"), nullable=False
    )
    universal_document_id = Column(String(32), nullable=True)
    analysis_report_id = Column(String(36), nullable=True)
    schema_name = Column(String(64), nullable=False)
    schema_version = Column(String(32), nullable=False, default="1.0.0")
    extraction_version = Column(String(32), nullable=False, default="1.0.0")
    status = Column(String(48), nullable=False, default=ExtractionStatus.PENDING.value)
    # Scope pour unicité soft : "active" tant que non superseded/cancelled/failed terminal
    status_scope = Column(String(16), nullable=False, default="active")
    strategy = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=True)
    model_name = Column(String(128), nullable=True)
    prompt_version = Column(String(64), nullable=True)
    input_fingerprint = Column(String(64), nullable=False)
    output_fingerprint = Column(String(64), nullable=True)
    structured_data = Column(JSON, nullable=False, default=dict)
    field_provenance = Column(JSON, nullable=False, default=dict)
    quality_summary = Column(JSON, nullable=False, default=dict)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    errors_json = Column("errors", JSON, nullable=False, default=list)
    overall_confidence = Column(Float, nullable=True)
    critical_fields_confidence = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    consistency_score = Column(Float, nullable=True)
    confidence_level = Column(String(32), nullable=True)
    requires_human_review = Column(Boolean, nullable=False, default=True)
    progress_percent = Column(Integer, nullable=False, default=0)
    current_step = Column(String(64), nullable=True)
    text_source = Column(String(64), nullable=True)
    text_character_count = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    token_usage = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentExtractionAttempt(Base):
    __tablename__ = "elfis_document_extraction_attempts"
    __table_args__ = (
        Index("ix_elfis_extr_attempt_extr", "extraction_id"),
        Index("ix_elfis_extr_attempt_org", "organization_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    extraction_id = Column(
        String(36), ForeignKey("elfis_document_extractions.id"), nullable=False
    )
    attempt_number = Column(Integer, nullable=False, default=1)
    extractor_name = Column(String(64), nullable=False)
    provider = Column(String(64), nullable=True)
    model_name = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    input_metadata = Column(JSON, nullable=False, default=dict)
    output_metadata = Column(JSON, nullable=False, default=dict)
    token_usage = Column(JSON, nullable=False, default=dict)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message_safe = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
