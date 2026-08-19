"""Modèles SQLAlchemy — Document Intelligence."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class ElfisDocumentTextExtraction(Base):
    __tablename__ = "elfis_document_text_extractions"
    __table_args__ = (
        UniqueConstraint("extraction_id", name="uq_elfis_doc_text_extraction_id"),
        UniqueConstraint(
            "organization_id",
            "vault_document_id",
            "document_version",
            name="uq_elfis_doc_text_org_doc_ver",
        ),
        CheckConstraint(
            "status IN ("
            "'pending','processing','completed','blocked',"
            "'failed','requires_ocr','requires_review','cancelled'"
            ")",
            name="ck_elfis_doc_text_status",
        ),
        Index("ix_elfis_doc_text_organization_id", "organization_id"),
        Index("ix_elfis_doc_text_vault_document_id", "vault_document_id"),
        Index("ix_elfis_doc_text_status", "status"),
        Index("ix_elfis_doc_text_extractor_name", "extractor_name"),
        Index("ix_elfis_doc_text_created_at", "created_at"),
        Index("ix_elfis_doc_text_job_id", "job_id"),
        Index("ix_elfis_doc_text_correlation_id", "correlation_id"),
        Index("ix_elfis_doc_text_idempotency_key", "idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    extraction_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vault_document_id = Column(String(36), nullable=False, index=True)
    document_version = Column(Integer, nullable=False, default=1)

    extractor_name = Column(String(64), nullable=False, index=True)
    extractor_version = Column(String(32), nullable=True)
    provider = Column(String(64), nullable=True)

    status = Column(String(32), nullable=False, index=True)

    mime_type = Column(String(128), nullable=True)
    filename = Column(String(512), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    page_count = Column(Integer, nullable=True)

    text_content = Column(Text, nullable=True)
    text_hash = Column(String(64), nullable=True)
    text_length = Column(Integer, nullable=False, default=0)

    quality_score = Column(Numeric(5, 4), nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    requires_ocr = Column(Boolean, nullable=False, default=False)
    requires_review = Column(Boolean, nullable=False, default=False)

    language = Column(String(16), nullable=True)

    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    warnings = Column(JSON, nullable=False, default=list)
    errors = Column(JSON, nullable=False, default=list)

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
