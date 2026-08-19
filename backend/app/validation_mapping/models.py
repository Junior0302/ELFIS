"""Modèles SQLAlchemy — Validation & Mapping Center."""

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
from app.validation_mapping.enums import (
    FieldValidationStatus,
    MatchResolution,
    ValidationSessionStatus,
)


def _uuid() -> str:
    return str(uuid4())


class ElfisValidationSession(Base):
    __tablename__ = "elfis_validation_sessions"
    __table_args__ = (
        Index("ix_elfis_val_org_created", "organization_id", "created_at"),
        Index("ix_elfis_val_item", "document_intake_item_id"),
        Index("ix_elfis_val_session_mig", "migration_session_id"),
        Index("ix_elfis_val_status", "organization_id", "status"),
        UniqueConstraint(
            "organization_id",
            "document_intake_item_id",
            "extraction_id",
            name="uq_elfis_val_item_extraction",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(String(36), nullable=True)
    document_intake_item_id = Column(
        String(36), ForeignKey("elfis_document_intake_items.id"), nullable=False
    )
    universal_document_id = Column(String(32), nullable=True)
    extraction_id = Column(String(36), nullable=False)
    status = Column(
        String(32), nullable=False, default=ValidationSessionStatus.PENDING.value
    )
    validated_data = Column(JSON, nullable=False, default=dict)
    field_states = Column(JSON, nullable=False, default=dict)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    errors_json = Column("errors", JSON, nullable=False, default=list)
    duplicate_summary = Column(JSON, nullable=False, default=dict)
    matching_summary = Column(JSON, nullable=False, default=dict)
    progress_percent = Column(Integer, nullable=False, default=0)
    rejection_reason = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisValidationField(Base):
    __tablename__ = "elfis_validation_fields"
    __table_args__ = (
        Index("ix_elfis_val_field_session", "validation_session_id"),
        UniqueConstraint(
            "validation_session_id",
            "field_path",
            name="uq_elfis_val_field_path",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    validation_session_id = Column(
        String(36), ForeignKey("elfis_validation_sessions.id"), nullable=False
    )
    field_path = Column(String(255), nullable=False)
    ai_value = Column(JSON, nullable=True)
    current_value = Column(JSON, nullable=True)
    status = Column(
        String(32), nullable=False, default=FieldValidationStatus.UNKNOWN.value
    )
    confidence = Column(Float, nullable=True)
    provenance = Column(JSON, nullable=False, default=dict)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisValidationHistory(Base):
    """Append-only — jamais d'UPDATE/DELETE métier."""

    __tablename__ = "elfis_validation_history"
    __table_args__ = (
        Index("ix_elfis_val_hist_session", "validation_session_id", "created_at"),
        Index("ix_elfis_val_hist_org", "organization_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    validation_session_id = Column(
        String(36), ForeignKey("elfis_validation_sessions.id"), nullable=False
    )
    field_path = Column(String(255), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    action = Column(String(32), nullable=False)  # edit|accept|reject|ignore_warning
    reason = Column(Text, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisValidationDuplicate(Base):
    __tablename__ = "elfis_validation_duplicates"
    __table_args__ = (Index("ix_elfis_val_dup_session", "validation_session_id"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    validation_session_id = Column(
        String(36), ForeignKey("elfis_validation_sessions.id"), nullable=False
    )
    other_document_id = Column(String(36), nullable=True)
    other_universal_document_id = Column(String(32), nullable=True)
    severity = Column(String(32), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    matched_fields = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=True)
    resolution = Column(String(32), nullable=False, default="unresolved")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisValidationMatch(Base):
    __tablename__ = "elfis_validation_matches"
    __table_args__ = (Index("ix_elfis_val_match_session", "validation_session_id"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    validation_session_id = Column(
        String(36), ForeignKey("elfis_validation_sessions.id"), nullable=False
    )
    party_role = Column(String(32), nullable=False)  # supplier|customer|merchant
    category = Column(String(32), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    contact_id = Column(Integer, nullable=True)
    contact_label = Column(String(255), nullable=True)
    matched_criteria = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=True)
    resolution = Column(
        String(32), nullable=False, default=MatchResolution.UNRESOLVED.value
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
