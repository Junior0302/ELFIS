"""Modèles SQLAlchemy extraction results / fields / reviews."""

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


class ElfisDocumentExtractionResult(Base):
    __tablename__ = "elfis_document_extraction_results"
    __table_args__ = (
        # Préfixe ix_elfis_dpextr_* : namespace distinct de document_extraction
        # (Migration Center) — SQLite/PG exigent des noms d'index uniques au schéma.
        Index("ix_elfis_dpextr_org_created", "organization_id", "created_at"),
        Index("ix_elfis_dpextr_document_created", "document_id", "created_at"),
        Index("ix_elfis_dpextr_version", "document_version_id"),
        Index("ix_elfis_dpextr_ocr", "ocr_result_id"),
        Index("ix_elfis_dpextr_job", "processing_job_id"),
        Index("ix_elfis_dpextr_status_created", "status", "created_at"),
        Index("ix_elfis_dpextr_schema", "schema_key", "schema_version"),
        Index("ix_elfis_dpextr_provider", "provider_key", "provider_version"),
        Index("ix_elfis_dpextr_review_status", "requires_review", "status"),
        UniqueConstraint(
            "document_version_id",
            "ocr_result_id",
            "schema_key",
            "schema_version",
            "provider_key",
            "provider_version",
            "idempotency_hash",
            name="uq_elfis_dpextr_idempotency",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    document_id = Column(String(36), nullable=False, index=True)
    document_version_id = Column(String(36), nullable=False)
    processing_job_id = Column(
        String(36),
        ForeignKey("elfis_document_processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    ocr_result_id = Column(String(36), nullable=True)
    classification_id = Column(String(36), nullable=True)
    schema_key = Column(String(64), nullable=False)
    schema_version = Column(String(32), nullable=False)
    provider_key = Column(String(64), nullable=False)
    provider_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    confidence_score = Column(Float, nullable=True)
    requires_review = Column(Boolean, nullable=False, default=True)
    fields_count = Column(Integer, nullable=False, default=0)
    valid_fields_count = Column(Integer, nullable=False, default=0)
    invalid_fields_count = Column(Integer, nullable=False, default=0)
    missing_required_fields_count = Column(Integer, nullable=False, default=0)
    result_artifact_storage_object_id = Column(String(36), nullable=True)
    result_checksum_sha256 = Column(String(64), nullable=True)
    validation_summary_json = Column(JSON, nullable=True)
    warnings_json = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message_sanitized = Column(String(255), nullable=True)
    selection_reason_code = Column(String(64), nullable=True)
    source_reason_code = Column(String(64), nullable=True)
    effective_document_type = Column(String(64), nullable=True)
    idempotency_hash = Column(String(64), nullable=False, default="default")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentExtractedField(Base):
    """Index de revue — valeurs sensibles masquées ; contenu complet dans l'artefact."""

    __tablename__ = "elfis_document_extracted_fields"
    __table_args__ = (
        UniqueConstraint("extraction_result_id", "field_path", name="uq_elfis_dpextr_field_path"),
        Index("ix_elfis_dpextr_fields_result", "extraction_result_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    extraction_result_id = Column(
        String(36),
        ForeignKey("elfis_document_extraction_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_path = Column(String(128), nullable=False)
    field_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="extracted")
    # valeur normalisée bornée — champs non sensibles seulement ; sinon null
    normalized_value_json = Column(JSON, nullable=True)
    display_value_masked = Column(String(120), nullable=True)
    confidence_score = Column(Float, nullable=True)
    source_page = Column(Integer, nullable=True)
    evidence_reference_json = Column(JSON, nullable=True)
    validation_codes_json = Column(JSON, nullable=True)
    manually_corrected = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentExtractionReview(Base):
    __tablename__ = "elfis_document_extraction_reviews"
    __table_args__ = (Index("ix_elfis_dpextr_reviews_result", "extraction_result_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    extraction_result_id = Column(
        String(36),
        ForeignKey("elfis_document_extraction_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String(32), nullable=False)  # confirm|reject|correct
    actor_user_id = Column(Integer, nullable=True)
    reason = Column(String(255), nullable=True)
    # patch : field_path → {provider_value, corrected_value} sans dump massif
    patch_summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
