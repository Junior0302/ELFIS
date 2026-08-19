"""Modèle elfis_security_events."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisSecurityEvent(Base):
    __tablename__ = "elfis_security_events"
    __table_args__ = (
        UniqueConstraint("security_event_id", name="uq_elfis_security_event_id"),
        CheckConstraint(
            "severity IN ('info','warning','error','critical')",
            name="ck_elfis_security_event_severity",
        ),
        Index("ix_elfis_security_events_type", "event_type"),
        Index("ix_elfis_security_events_created", "created_at"),
        Index("ix_elfis_security_events_org", "organization_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    security_event_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, default="warning")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ip_hash = Column(String(64), nullable=True)
    route = Column(String(255), nullable=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(128), nullable=True)
    details = Column(JSON, nullable=True)
    request_id = Column(String(64), nullable=True)
    correlation_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
