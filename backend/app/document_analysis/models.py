"""Modèles SQLAlchemy — Document Analysis reports."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.types import JSON

from app.database import Base
from app.document_analysis.enums import AnalysisReportStatus


def _uuid() -> str:
    return str(uuid4())


class ElfisDocumentAnalysisReport(Base):
    __tablename__ = "elfis_document_analysis_reports"
    __table_args__ = (
        Index("ix_elfis_analysis_org_created", "organization_id", "created_at"),
        Index("ix_elfis_analysis_item", "document_intake_item_id"),
        Index("ix_elfis_analysis_session", "migration_session_id"),
        Index("ix_elfis_analysis_status", "organization_id", "status"),
        Index("ix_elfis_analysis_universal", "universal_document_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    document_intake_item_id = Column(
        String(36), ForeignKey("elfis_document_intake_items.id"), nullable=False
    )
    universal_document_id = Column(String(32), nullable=True)
    migration_session_id = Column(String(36), nullable=True)
    status = Column(String(32), nullable=False, default=AnalysisReportStatus.PENDING.value)
    schema_version = Column(Integer, nullable=False, default=1)
    analysis_version = Column(String(32), nullable=False, default="1.0.0")
    report_json = Column("report", JSON, nullable=False, default=dict)
    need_ocr = Column(Boolean, nullable=True)
    classification_label = Column(String(64), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    language_code = Column(String(16), nullable=True)
    language_confidence = Column(Float, nullable=True)
    quality_score = Column(Integer, nullable=True)
    orientation_degrees = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    detected_format = Column(String(32), nullable=True)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    current_step = Column(String(64), nullable=True)
    steps_completed = Column(Integer, nullable=False, default=0)
    steps_total = Column(Integer, nullable=False, default=12)
    version = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
