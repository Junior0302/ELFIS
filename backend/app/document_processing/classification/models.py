"""Modèle ElfisDocumentClassification."""

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


class ElfisDocumentClassification(Base):
    __tablename__ = "elfis_document_classifications"
    __table_args__ = (
        Index("ix_elfis_doc_class_org_created", "organization_id", "created_at"),
        Index("ix_elfis_doc_class_document_created", "document_id", "created_at"),
        Index("ix_elfis_doc_class_version", "document_version_id"),
        Index("ix_elfis_doc_class_status_created", "status", "created_at"),
        Index("ix_elfis_doc_class_predicted", "predicted_type"),
        Index("ix_elfis_doc_class_confirmed", "confirmed_type"),
        Index("ix_elfis_doc_class_review_status", "requires_review", "status"),
        Index("ix_elfis_doc_class_classifier", "classifier_key", "classifier_version"),
        Index(
            "ix_elfis_doc_class_active_lookup",
            "document_version_id",
            "classifier_key",
            "classifier_version",
            "status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    document_version_id = Column(String(36), nullable=False)
    processing_job_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    classifier_key = Column(String(64), nullable=False)
    classifier_version = Column(String(32), nullable=False)
    predicted_type = Column(String(64), nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="proposed")
    requires_review = Column(Boolean, nullable=False, default=True)
    evidence_json = Column(JSON, nullable=True)
    alternatives_json = Column(JSON, nullable=True)
    source = Column(String(32), nullable=False, default="pipeline")
    confirmed_type = Column(String(64), nullable=True)
    confirmed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
