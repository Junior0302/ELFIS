"""Modèles SQLAlchemy — elfis_audit_events (+ archive)."""

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
    Text,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisAuditEvent(Base):
    __tablename__ = "elfis_audit_events"
    __table_args__ = (
        Index("ix_elfis_audit_events_occurred_at", "occurred_at"),
        Index("ix_elfis_audit_events_action", "action"),
        Index("ix_elfis_audit_events_actor_user_id", "actor_user_id"),
        Index("ix_elfis_audit_events_organization_id", "organization_id"),
        Index("ix_elfis_audit_events_product", "product"),
        Index("ix_elfis_audit_events_service", "service"),
        Index("ix_elfis_audit_events_severity", "severity"),
        Index("ix_elfis_audit_events_correlation_id", "correlation_id"),
        Index("ix_elfis_audit_events_request_id", "request_id"),
        Index("ix_elfis_audit_events_category", "category"),
        Index("ix_elfis_audit_events_status", "status"),
        # Composites RC2.3 étape 3 (requêtes filtrées + tri chronologique)
        Index("ix_elfis_audit_cat_occurred", "category", "occurred_at"),
        Index("ix_elfis_audit_sev_occurred", "severity", "occurred_at"),
        Index("ix_elfis_audit_actor_occurred", "actor_user_id", "occurred_at"),
        Index("ix_elfis_audit_org_occurred", "organization_id", "occurred_at"),
        Index("ix_elfis_audit_action_occurred", "action", "occurred_at"),
        Index("ix_elfis_audit_success_occurred", "success", "occurred_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    severity = Column(String(16), nullable=False, default="INFO")
    category = Column(String(32), nullable=False, default="OTHER")
    action = Column(String(128), nullable=False)
    status = Column(String(16), nullable=False, default="SUCCESS")
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(255), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    product = Column(String(64), nullable=True)
    service = Column(String(64), nullable=True)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(128), nullable=True)
    target_display = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)


class ElfisAuditEventArchive(Base):
    """Copie archivée — aucune modification des événements actifs."""

    __tablename__ = "elfis_audit_events_archive"
    __table_args__ = (
        Index("ix_elfis_audit_arch_occurred_at", "occurred_at"),
        Index("ix_elfis_audit_arch_archived_at", "archived_at"),
        Index("ix_elfis_audit_arch_batch", "archive_batch_id"),
        Index("ix_elfis_audit_arch_category", "category"),
    )

    id = Column(String(36), primary_key=True)
    occurred_at = Column(DateTime, nullable=False)
    severity = Column(String(16), nullable=False, default="INFO")
    category = Column(String(32), nullable=False, default="OTHER")
    action = Column(String(128), nullable=False)
    status = Column(String(16), nullable=False, default="SUCCESS")
    actor_user_id = Column(Integer, nullable=True)
    actor_email = Column(String(255), nullable=True)
    organization_id = Column(Integer, nullable=True)
    product = Column(String(64), nullable=True)
    service = Column(String(64), nullable=True)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(128), nullable=True)
    target_display = Column(String(255), nullable=True)
    request_id = Column(String(64), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    archived_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    archive_batch_id = Column(String(36), nullable=False, default=_uuid)
    archive_reason = Column(String(128), nullable=True)
