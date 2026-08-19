"""Modèles SQLAlchemy product document packages / deliveries."""

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
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisProductProcessingPackage(Base):
    __tablename__ = "elfis_product_processing_packages"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_elfis_pkg_idempotency"),
        Index("ix_elfis_pkg_org_created", "organization_id", "created_at"),
        Index("ix_elfis_pkg_document_created", "document_id", "created_at"),
        Index("ix_elfis_pkg_version", "document_version_id"),
        Index("ix_elfis_pkg_extraction", "extraction_result_id"),
        Index("ix_elfis_pkg_validation", "business_validation_id"),
        Index("ix_elfis_pkg_product_status", "product_key", "status"),
        Index("ix_elfis_pkg_status_created", "status", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    product_key = Column(String(64), nullable=False)
    document_id = Column(String(36), nullable=False, index=True)
    document_version_id = Column(String(36), nullable=False)
    classification_id = Column(String(36), nullable=True)
    ocr_result_id = Column(String(36), nullable=True)
    extraction_result_id = Column(String(36), nullable=False)
    business_validation_id = Column(String(36), nullable=False)
    package_schema_key = Column(String(64), nullable=False)
    package_schema_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    content_artifact_storage_object_id = Column(String(36), nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    idempotency_key = Column(String(128), nullable=False)
    created_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisProductDocumentDelivery(Base):
    __tablename__ = "elfis_product_document_deliveries"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_elfis_del_idempotency"),
        Index("ix_elfis_del_package", "package_id"),
        Index("ix_elfis_del_product_status", "product_key", "status"),
        Index("ix_elfis_del_status_retry", "status", "next_retry_at"),
        Index("ix_elfis_del_locked", "locked_until"),
        Index("ix_elfis_del_org_created", "organization_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    package_id = Column(
        String(36),
        ForeignKey("elfis_product_processing_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_key = Column(String(64), nullable=False)
    bridge_key = Column(String(64), nullable=False)
    bridge_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    idempotency_key = Column(String(128), nullable=False)
    external_reference = Column(String(128), nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message_sanitized = Column(String(255), nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    locked_by = Column(String(64), nullable=True)
    locked_until = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElfisProductDocumentDeliveryAttempt(Base):
    __tablename__ = "elfis_product_document_delivery_attempts"
    __table_args__ = (
        Index("ix_elfis_del_att_delivery", "delivery_id"),
        Index("ix_elfis_del_att_number", "delivery_id", "attempt_number"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    delivery_id = Column(
        String(36),
        ForeignKey("elfis_product_document_deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="started")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    response_code = Column(String(64), nullable=True)
    error_code = Column(String(64), nullable=True)
    retryable = Column(Boolean, nullable=False, default=False)
    metadata_json = Column(JSON, nullable=True)
