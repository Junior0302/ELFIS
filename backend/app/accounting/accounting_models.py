"""Modèles SQLAlchemy — Accounting Pipeline."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
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


class ElfisAccountingProposal(Base):
    __tablename__ = "elfis_accounting_proposals"
    __table_args__ = (
        UniqueConstraint("proposal_id", name="uq_elfis_acc_proposal_id"),
        UniqueConstraint(
            "organization_id",
            "vault_document_id",
            "document_version",
            name="uq_elfis_acc_proposal_org_doc_ver",
        ),
        CheckConstraint(
            "status IN ("
            "'pending','processing','validation_failed','financial_error',"
            "'mapping_failed','requires_review','ready_for_validation',"
            "'validated','rejected','cancelled','failed'"
            ")",
            name="ck_elfis_acc_proposal_status",
        ),
        Index("ix_elfis_acc_proposal_organization_id", "organization_id"),
        Index("ix_elfis_acc_proposal_vault_document_id", "vault_document_id"),
        Index("ix_elfis_acc_proposal_status", "status"),
        Index("ix_elfis_acc_proposal_document_type", "document_type"),
        Index("ix_elfis_acc_proposal_created_at", "created_at"),
        Index("ix_elfis_acc_proposal_job_id", "job_id"),
        Index("ix_elfis_acc_proposal_idempotency_key", "idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    proposal_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    vault_document_id = Column(String(36), nullable=False, index=True)
    document_analysis_id = Column(String(36), nullable=True)
    document_version = Column(Integer, nullable=False, default=1)

    document_type = Column(String(64), nullable=False, index=True)
    document_number = Column(String(128), nullable=True)
    document_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)

    supplier_name = Column(String(255), nullable=True)
    customer_name = Column(String(255), nullable=True)

    currency = Column(String(8), nullable=False, default="EUR")

    amount_ht = Column(Numeric(14, 2), nullable=True)
    amount_vat = Column(Numeric(14, 2), nullable=True)
    amount_ttc = Column(Numeric(14, 2), nullable=True)

    status = Column(String(32), nullable=False, index=True)
    current_stage = Column(String(64), nullable=False)

    document_validation = Column(JSON, nullable=False, default=dict)
    financial_validation = Column(JSON, nullable=False, default=dict)
    accounting_mapping = Column(JSON, nullable=False, default=dict)
    quality_summary = Column(JSON, nullable=False, default=dict)

    confidence = Column(Numeric(5, 4), nullable=True)
    requires_review = Column(Boolean, nullable=False, default=False)
    review_reasons = Column(JSON, nullable=False, default=list)

    source = Column(String(64), nullable=False, default="elfis_pipeline")

    job_id = Column(String(36), nullable=True, index=True)
    correlation_id = Column(String(36), nullable=True)
    source_event_id = Column(String(36), nullable=True)
    idempotency_key = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)


class ElfisAccountingEntry(Base):
    __tablename__ = "elfis_accounting_entries"
    __table_args__ = (
        UniqueConstraint("entry_id", name="uq_elfis_acc_entry_id"),
        Index("ix_elfis_acc_entry_organization_id", "organization_id"),
        Index("ix_elfis_acc_entry_proposal_id", "proposal_id"),
        Index("ix_elfis_acc_entry_status", "status"),
        CheckConstraint(
            "status IN ('draft','proposed','validated','exported','cancelled')",
            name="ck_elfis_acc_entry_status",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    entry_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    proposal_id = Column(String(36), nullable=False, index=True)

    journal_code = Column(String(16), nullable=False)
    entry_date = Column(Date, nullable=False)
    reference = Column(String(128), nullable=True)
    description = Column(String(500), nullable=False)
    currency = Column(String(8), nullable=False, default="EUR")

    total_debit = Column(Numeric(14, 2), nullable=False, default=0)
    total_credit = Column(Numeric(14, 2), nullable=False, default=0)
    balanced = Column(Boolean, nullable=False, default=False)

    status = Column(String(32), nullable=False, default="proposed", index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    validated_at = Column(DateTime, nullable=True)


class ElfisAccountingEntryLine(Base):
    __tablename__ = "elfis_accounting_entry_lines"
    __table_args__ = (
        UniqueConstraint("line_id", name="uq_elfis_acc_line_id"),
        UniqueConstraint("entry_id", "line_number", name="uq_elfis_acc_line_entry_num"),
        CheckConstraint("debit >= 0", name="ck_elfis_acc_line_debit"),
        CheckConstraint("credit >= 0", name="ck_elfis_acc_line_credit"),
        CheckConstraint(
            "NOT (debit > 0 AND credit > 0)",
            name="ck_elfis_acc_line_single_side",
        ),
        Index("ix_elfis_acc_line_organization_id", "organization_id"),
        Index("ix_elfis_acc_line_entry_id", "entry_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    line_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    entry_id = Column(String(36), nullable=False, index=True)

    line_number = Column(Integer, nullable=False)

    account_code = Column(String(16), nullable=False)
    account_label = Column(String(255), nullable=True)
    third_party_name = Column(String(255), nullable=True)

    debit = Column(Numeric(14, 2), nullable=False, default=0)
    credit = Column(Numeric(14, 2), nullable=False, default=0)

    vat_rate = Column(Numeric(6, 3), nullable=True)
    vat_code = Column(String(32), nullable=True)

    description = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ElfisAccountingReview(Base):
    __tablename__ = "elfis_accounting_reviews"
    __table_args__ = (
        UniqueConstraint("review_id", name="uq_elfis_acc_review_id"),
        Index("ix_elfis_acc_review_organization_id", "organization_id"),
        Index("ix_elfis_acc_review_proposal_id", "proposal_id"),
        Index("ix_elfis_acc_review_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    review_id = Column(String(36), nullable=False, unique=True, default=_uuid, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    proposal_id = Column(String(36), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    action = Column(String(64), nullable=False)

    previous_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)

    comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
