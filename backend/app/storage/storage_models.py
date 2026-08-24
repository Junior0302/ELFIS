"""Modèles SQLAlchemy — storage / documents / versions / legal hold / tombstones."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisStorageObject(Base):
    __tablename__ = "elfis_storage_objects"
    __table_args__ = (
        UniqueConstraint("provider", "namespace", "object_key", name="uq_elfis_storage_object_key"),
        Index("ix_elfis_storage_objects_org", "organization_id"),
        Index("ix_elfis_storage_objects_status", "status"),
        Index("ix_elfis_storage_objects_checksum", "checksum_sha256"),
        Index("ix_elfis_storage_objects_created", "created_at"),
        Index("ix_elfis_storage_objects_status_created", "status", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    provider = Column(String(32), nullable=False, default="local")
    namespace = Column(String(128), nullable=False, default="default")
    object_key = Column(String(512), nullable=False)
    original_filename = Column(String(255), nullable=False)
    safe_filename = Column(String(255), nullable=False)
    mime_type_declared = Column(String(128), nullable=True)
    mime_type_detected = Column(String(128), nullable=True)
    extension = Column(String(32), nullable=True)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    checksum_sha256 = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    encryption_status = Column(String(32), nullable=False, default="none")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class ElfisDocumentRecord(Base):
    __tablename__ = "elfis_document_records"
    __table_args__ = (
        Index("ix_elfis_document_records_org", "organization_id"),
        Index("ix_elfis_document_records_status", "status"),
        Index("ix_elfis_document_records_type", "document_type"),
        Index("ix_elfis_document_records_created", "created_at"),
        Index("ix_elfis_document_records_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_elfis_document_records_deleted_at", "deleted_at"),
        Index("ix_elfis_document_records_retention", "retention_deadline"),
        Index("ix_elfis_document_records_purge_status", "purge_status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_type = Column(String(64), nullable=False, default="file")
    title = Column(String(255), nullable=False, default="")
    status = Column(String(32), nullable=False, default="draft")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    product = Column(String(64), nullable=True)
    # Compat étape 1–2
    current_storage_object_id = Column(
        String(36),
        ForeignKey("elfis_storage_objects.id"),
        nullable=True,
    )
    # Étape 3
    current_version_id = Column(String(36), nullable=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source = Column(String(32), nullable=False, default="upload")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    purged_at = Column(DateTime, nullable=True)
    retention_deadline = Column(DateTime, nullable=True)
    purge_status = Column(String(32), nullable=False, default="none")
    deleted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    delete_reason = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class ElfisDocumentVersion(Base):
    """Version immuable — contenu figé ; seuls status / dates de cycle évoluent."""

    __tablename__ = "elfis_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_elfis_document_version_num"),
        Index("ix_elfis_document_versions_document", "document_id"),
        Index("ix_elfis_document_versions_document_created", "document_id", "created_at"),
        Index("ix_elfis_document_versions_storage", "storage_object_id"),
        Index("ix_elfis_document_versions_status_created", "status", "created_at"),
        Index("ix_elfis_document_versions_deleted_at", "deleted_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(
        String(36),
        ForeignKey("elfis_document_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    storage_object_id = Column(
        String(36),
        ForeignKey("elfis_storage_objects.id"),
        nullable=False,
    )
    status = Column(String(32), nullable=False, default="current")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source = Column(String(32), nullable=False, default="upload")
    change_reason = Column(String(255), nullable=True)
    # Figés à la création
    original_filename = Column(String(255), nullable=False, default="")
    size_bytes = Column(BigInteger, nullable=False, default=0)
    checksum_sha256 = Column(String(64), nullable=True)
    mime_type = Column(String(128), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    superseded_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)


class ElfisDocumentLink(Base):
    __tablename__ = "elfis_document_links"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "entity_type",
            "entity_id",
            "relation_type",
            name="uq_elfis_document_link",
        ),
        Index("ix_elfis_document_links_document", "document_id"),
        Index("ix_elfis_document_links_entity", "entity_type", "entity_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(
        String(36),
        ForeignKey("elfis_document_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(128), nullable=False)
    relation_type = Column(String(64), nullable=False, default="attachment")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class ElfisDocumentLegalHold(Base):
    __tablename__ = "elfis_document_legal_holds"
    __table_args__ = (
        Index("ix_elfis_legal_holds_document", "document_id"),
        Index("ix_elfis_legal_holds_document_active", "document_id", "active"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(
        String(36),
        ForeignKey("elfis_document_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason = Column(String(500), nullable=False)
    reference = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    placed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    placed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    released_at = Column(DateTime, nullable=True)
    released_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class ElfisDocumentTombstone(Base):
    """Preuve minimale post-purge — pas de contenu ni chemin."""

    __tablename__ = "elfis_document_tombstones"
    __table_args__ = (
        Index("ix_elfis_tombstones_org", "organization_id"),
        Index("ix_elfis_tombstones_purged", "purged_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, unique=True)
    organization_id = Column(Integer, nullable=False)
    document_type = Column(String(64), nullable=True)
    title_redacted = Column(String(64), nullable=True)
    source = Column(String(32), nullable=True)
    created_at_original = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    purged_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    purged_by_user_id = Column(Integer, nullable=True)
    purge_reason = Column(String(255), nullable=True)
    checksum_prefix = Column(String(16), nullable=True)
    version_count = Column(Integer, nullable=False, default=0)
    audit_reference = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)


class ElfisStorageMigration(Base):
    """Trace de migration progressive local → distant."""

    __tablename__ = "elfis_storage_migrations"
    __table_args__ = (
        Index("ix_elfis_storage_migrations_status_created", "status", "created_at"),
        Index("ix_elfis_storage_migrations_object", "storage_object_id"),
        Index("ix_elfis_storage_migrations_source", "source_provider"),
        Index("ix_elfis_storage_migrations_target", "target_provider"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    storage_object_id = Column(
        String(36),
        ForeignKey("elfis_storage_objects.id"),
        nullable=False,
    )
    source_provider = Column(String(32), nullable=False)
    source_namespace = Column(String(128), nullable=False)
    source_object_key = Column(String(512), nullable=False)
    target_provider = Column(String(32), nullable=False)
    target_namespace = Column(String(128), nullable=False)
    target_object_key = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    checksum_verified = Column(Boolean, nullable=False, default=False)
    source_deleted_at = Column(DateTime, nullable=True)
    error_code = Column(String(64), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
