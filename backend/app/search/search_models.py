"""Modèles SQLAlchemy — Search Engine."""

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
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisSearchDocument(Base):
    __tablename__ = "elfis_search_documents"
    __table_args__ = (
        UniqueConstraint("search_document_id", name="uq_elfis_search_document_id"),
        UniqueConstraint(
            "organization_id",
            "resource_type",
            "resource_id",
            "resource_version",
            name="uq_elfis_search_org_res_ver",
        ),
        Index("ix_elfis_search_organization_id", "organization_id"),
        Index("ix_elfis_search_resource_type", "resource_type"),
        Index("ix_elfis_search_resource_id", "resource_id"),
        Index("ix_elfis_search_status", "status"),
        Index("ix_elfis_search_category", "category"),
        Index("ix_elfis_search_document_date", "document_date"),
        Index("ix_elfis_search_amount", "amount"),
        Index("ix_elfis_search_is_active", "is_active"),
        Index("ix_elfis_search_indexed_at", "indexed_at"),
        Index("ix_elfis_search_content_hash", "content_hash"),
        Index("ix_elfis_search_idempotency_key", "idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    search_document_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False, index=True)
    resource_version = Column(Integer, nullable=False, default=1)

    title = Column(String(512), nullable=False)
    subtitle = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    search_text = Column(Text, nullable=False)

    status = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=True, index=True)

    document_date = Column(DateTime, nullable=True, index=True)
    amount = Column(Numeric(18, 2), nullable=True, index=True)
    currency = Column(String(8), nullable=True)

    action_url = Column(String(512), nullable=True)

    metadata_json = Column("metadata", JSON, nullable=False, default=dict)

    # tsvector Postgres géré par trigger SQL — colonne optionnelle côté ORM (Text pour SQLite)
    search_vector = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True, index=True)

    indexed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    source_event_id = Column(String(36), nullable=True)
    correlation_id = Column(String(36), nullable=True)

    content_hash = Column(String(64), nullable=True, index=True)
    idempotency_key = Column(String(255), nullable=True, index=True)
