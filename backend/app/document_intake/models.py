"""Modèles SQLAlchemy — Document Intake Sprint 2.5."""

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
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base
from app.document_intake.enums import (
    DocumentLifecycleStatus,
    DuplicateType,
    IntakeOrigin,
    UploadSessionStatus,
)

# Les FKs ci-dessous référencent elfis_migration_sessions : la table cible doit
# être enregistrée dans Base.metadata sinon create_all() échoue (NoReferencedTableError).
from app.migration_center import models as _migration_models  # noqa: E402, F401


def _uuid() -> str:
    return str(uuid4())


class ElfisDocumentDocIdCounter(Base):
    """Compteur annuel pour Universal Document ID (DOC-YYYY-XXXXXXXX)."""

    __tablename__ = "elfis_document_doc_id_counters"

    year = Column(Integer, primary_key=True)
    last_value = Column(BigInteger, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentUploadSession(Base):
    __tablename__ = "elfis_document_upload_sessions"
    __table_args__ = (
        UniqueConstraint("upload_session_token", name="uq_elfis_upload_session_token"),
        Index("ix_elfis_upload_sess_org", "organization_id", "created_at"),
        Index("ix_elfis_upload_sess_mig", "migration_session_id"),
        Index("ix_elfis_upload_sess_status", "organization_id", "status"),
        Index("ix_elfis_upload_sess_token", "organization_id", "upload_session_token"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    upload_session_token = Column(
        String(64), nullable=False, default=lambda: f"upl_{uuid4().hex}"
    )
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(
        String(36), ForeignKey("elfis_migration_sessions.id"), nullable=False
    )
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), nullable=False, default=UploadSessionStatus.CREATED.value)
    source_type = Column(String(32), nullable=False, default="manual")
    display_label = Column(String(128), nullable=True)
    expected_file_count = Column(Integer, nullable=False, default=0)
    received_file_count = Column(Integer, nullable=False, default=0)
    validated_file_count = Column(Integer, nullable=False, default=0)
    duplicate_file_count = Column(Integer, nullable=False, default=0)
    rejected_file_count = Column(Integer, nullable=False, default=0)
    cancelled_file_count = Column(Integer, nullable=False, default=0)
    quarantined_file_count = Column(Integer, nullable=False, default=0)
    expected_total_bytes = Column(BigInteger, nullable=False, default=0)
    received_total_bytes = Column(BigInteger, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    analytics_json = Column("analytics", JSON, nullable=False, default=dict)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisDocumentLifecycleEntry(Base):
    __tablename__ = "elfis_document_lifecycle_entries"
    __table_args__ = (
        Index("ix_elfis_lifecycle_org_item", "organization_id", "document_intake_item_id"),
        Index("ix_elfis_lifecycle_occurred", "organization_id", "occurred_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    document_intake_item_id = Column(
        String(36), ForeignKey("elfis_document_intake_items.id"), nullable=False
    )
    from_status = Column(String(64), nullable=True)
    to_status = Column(String(64), nullable=False)
    reason_code = Column(String(64), nullable=True)
    actor_type = Column(String(32), nullable=False, default="system")
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisDocumentIntakeItem(Base):
    __tablename__ = "elfis_document_intake_items"
    __table_args__ = (
        Index("ix_elfis_intake_org_created", "organization_id", "created_at"),
        Index("ix_elfis_intake_org_status", "organization_id", "status"),
        Index("ix_elfis_intake_session", "migration_session_id"),
        Index("ix_elfis_intake_checksum", "organization_id", "checksum_sha256"),
        Index("ix_elfis_intake_batch", "batch_id"),
        Index("ix_elfis_intake_org_token", "organization_id", "intake_token"),
        Index("ix_elfis_intake_universal_id", "universal_document_id"),
        Index("ix_elfis_intake_upload_session", "upload_session_id"),
        Index("ix_elfis_intake_idempotency", "organization_id", "idempotency_key"),
        UniqueConstraint("intake_token", name="uq_elfis_intake_token"),
        UniqueConstraint("universal_document_id", name="uq_elfis_universal_document_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    intake_token = Column(String(64), nullable=False, default=lambda: f"din_{uuid4().hex}")
    universal_document_id = Column(String(32), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    migration_session_id = Column(
        String(36), ForeignKey("elfis_migration_sessions.id"), nullable=True
    )
    upload_session_id = Column(
        String(36), ForeignKey("elfis_document_upload_sessions.id"), nullable=True
    )
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    batch_id = Column(String(36), nullable=True)
    original_filename = Column(String(255), nullable=False)
    normalized_filename = Column(String(255), nullable=False)
    relative_path = Column(String(512), nullable=True)
    extension = Column(String(32), nullable=False)
    format_id = Column(String(32), nullable=False)
    declared_mime = Column(String(128), nullable=True)
    detected_mime = Column(String(128), nullable=True)
    mime = Column(String(128), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    checksum_sha256 = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default=DocumentLifecycleStatus.UPLOADED.value)
    lifecycle_status = Column(
        String(64), nullable=False, default=DocumentLifecycleStatus.UPLOADED.value
    )
    origin = Column(String(32), nullable=False, default=IntakeOrigin.API.value)
    storage_key = Column(String(512), nullable=False)
    storage_provider = Column(String(32), nullable=False, default="local")
    storage_location = Column(String(512), nullable=True)
    storage_bucket_or_root = Column(String(255), nullable=True)
    storage_object_key = Column(String(512), nullable=True)
    storage_version = Column(String(64), nullable=True)
    storage_metadata = Column(JSON, nullable=False, default=dict)
    fingerprint = Column(JSON, nullable=False, default=dict)
    fingerprint_version = Column(Integer, nullable=False, default=2)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    duplicate_of_id = Column(String(36), nullable=True)
    duplicate_type = Column(String(16), nullable=False, default=DuplicateType.NONE.value)
    duplicate_of_item_id = Column(String(36), nullable=True)
    duplicate_confidence = Column(Float, nullable=True)
    duplicate_reason = Column(String(128), nullable=True)
    client_upload_id = Column(String(128), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    chunk_count = Column(Integer, nullable=True)
    received_chunk_count = Column(Integer, nullable=True)
    multipart_upload_id = Column(String(128), nullable=True)
    quarantine_reason = Column(String(255), nullable=True)
    reject_reason = Column(String(255), nullable=True)
    scan_verdict = Column(String(32), nullable=True)
    extract_later = Column(Boolean, nullable=False, default=False)
    preview_allowed = Column(Boolean, nullable=False, default=False)
    analysis_allowed = Column(Boolean, nullable=False, default=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    version = Column(Integer, nullable=False, default=1)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)
