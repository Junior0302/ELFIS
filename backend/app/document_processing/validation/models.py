"""Modèles SQLAlchemy validation métier."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisDocumentBusinessValidation(Base):
    __tablename__ = "elfis_document_business_validations"
    __table_args__ = (
        Index("ix_elfis_bv_org_created", "organization_id", "created_at"),
        Index("ix_elfis_bv_document_created", "document_id", "created_at"),
        Index("ix_elfis_bv_version", "document_version_id"),
        Index("ix_elfis_bv_extraction", "extraction_result_id"),
        Index("ix_elfis_bv_status_created", "status", "created_at"),
        Index("ix_elfis_bv_review", "requires_review", "status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), nullable=False, index=True)
    document_version_id = Column(String(36), nullable=False)
    extraction_result_id = Column(String(36), nullable=False)
    classification_id = Column(String(36), nullable=True)
    processing_job_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    rule_set_key = Column(String(64), nullable=False)
    rule_set_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    valid = Column(Boolean, nullable=False, default=False)
    blocking_issue_count = Column(Integer, nullable=False, default=0)
    warning_count = Column(Integer, nullable=False, default=0)
    info_count = Column(Integer, nullable=False, default=0)
    requires_review = Column(Boolean, nullable=False, default=False)
    validation_artifact_storage_object_id = Column(String(36), nullable=True)
    artifact_checksum_sha256 = Column(String(64), nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message_sanitized = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentValidationIssue(Base):
    __tablename__ = "elfis_document_validation_issues"
    __table_args__ = (
        Index("ix_elfis_bv_issues_validation", "business_validation_id"),
        Index("ix_elfis_bv_issues_code", "issue_code"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    business_validation_id = Column(
        String(36),
        ForeignKey("elfis_document_business_validations.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_key = Column(String(64), nullable=False)
    rule_version = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False)
    field_paths_json = Column(JSON, nullable=True)
    issue_code = Column(String(64), nullable=False)
    message_code = Column(String(64), nullable=True)
    parameters_json = Column(JSON, nullable=True)
    blocking = Column(Boolean, nullable=False, default=False)
    resolved = Column(Boolean, nullable=False, default=False)
    resolution_type = Column(String(32), nullable=True)
    resolved_by_user_id = Column(Integer, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
