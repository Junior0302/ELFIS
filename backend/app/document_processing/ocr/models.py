"""Modèles SQLAlchemy OCR results / pages."""

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
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisDocumentOCRResult(Base):
    __tablename__ = "elfis_document_ocr_results"
    __table_args__ = (
        Index("ix_elfis_ocr_org_created", "organization_id", "created_at"),
        Index("ix_elfis_ocr_document_created", "document_id", "created_at"),
        Index("ix_elfis_ocr_version", "document_version_id"),
        Index("ix_elfis_ocr_job", "processing_job_id"),
        Index("ix_elfis_ocr_status_created", "status", "created_at"),
        Index("ix_elfis_ocr_provider_created", "provider_key", "created_at"),
        Index("ix_elfis_ocr_review_status", "requires_review", "status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    document_version_id = Column(String(36), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    processing_job_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_key = Column(String(64), nullable=False)
    provider_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    extraction_method = Column(String(64), nullable=False, default="unknown")
    page_count = Column(Integer, nullable=False, default=0)
    processed_page_count = Column(Integer, nullable=False, default=0)
    detected_languages_json = Column(JSON, nullable=True)
    average_confidence = Column(Float, nullable=True)
    text_artifact_storage_object_id = Column(String(36), nullable=True)
    text_length = Column(Integer, nullable=False, default=0)
    text_checksum_sha256 = Column(String(64), nullable=True)
    requires_review = Column(Boolean, nullable=False, default=False)
    warnings_json = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message_sanitized = Column(String(255), nullable=True)
    selection_reason_code = Column(String(64), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentOCRPage(Base):
    __tablename__ = "elfis_document_ocr_pages"
    __table_args__ = (
        UniqueConstraint("ocr_result_id", "page_number", name="uq_elfis_ocr_page_num"),
        Index("ix_elfis_ocr_pages_result", "ocr_result_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    ocr_result_id = Column(
        String(36),
        ForeignKey("elfis_document_ocr_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    character_count = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    detected_language = Column(String(16), nullable=True)
    rotation_degrees = Column(Float, nullable=True)
    text_checksum_sha256 = Column(String(64), nullable=True)
    warnings_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
