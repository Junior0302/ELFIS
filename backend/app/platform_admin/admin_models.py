"""Modèles Platform Admin — audit enrichi + incidents opérationnels."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
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


class ElfisAdminAuditLog(Base):
    __tablename__ = "elfis_admin_audit_logs"
    __table_args__ = (
        UniqueConstraint("audit_id", name="uq_elfis_admin_audit_id"),
        CheckConstraint(
            "status IN ('succeeded','failed','denied')",
            name="ck_elfis_admin_audit_status",
        ),
        Index("ix_elfis_admin_audit_actor", "actor_user_id"),
        Index("ix_elfis_admin_audit_org", "organization_id"),
        Index("ix_elfis_admin_audit_action", "action"),
        Index("ix_elfis_admin_audit_created", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    audit_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    actor_email = Column(String(255), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    action = Column(String(128), nullable=False, index=True)
    target_type = Column(String(64), nullable=False)
    target_id = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    request_id = Column(String(64), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent_summary = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False)
    error_code = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisOperationalIncident(Base):
    __tablename__ = "elfis_operational_incidents"
    __table_args__ = (
        UniqueConstraint("incident_id", name="uq_elfis_incident_id"),
        UniqueConstraint(
            "source_type",
            "source_id",
            "incident_type",
            name="uq_elfis_incident_source",
        ),
        CheckConstraint(
            "severity IN ('info','warning','error','critical')",
            name="ck_elfis_incident_severity",
        ),
        CheckConstraint(
            "status IN ('open','acknowledged','resolved','ignored')",
            name="ck_elfis_incident_status",
        ),
        Index("ix_elfis_incidents_organization_id", "organization_id"),
        Index("ix_elfis_incidents_status", "status"),
        Index("ix_elfis_incidents_type", "incident_type"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    incident_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    incident_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, index=True)
    source_type = Column(String(64), nullable=False)
    source_id = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
