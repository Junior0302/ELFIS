"""Modèles Accounting Engine V2."""

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
from app.accounting_engine.enums import ProposalV2Status


def _uuid() -> str:
    return str(uuid4())


class ElfisChartOfAccount(Base):
    """Plan comptable multi-plans (référence pour AccountResolver)."""

    __tablename__ = "elfis_chart_of_accounts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "plan_code", "account_code", name="uq_elfis_coa_org_plan_code"
        ),
        Index("ix_elfis_coa_org", "organization_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    plan_code = Column(String(32), nullable=False, default="pcg_fr")
    account_code = Column(String(16), nullable=False)
    account_label = Column(String(255), nullable=False, default="")
    account_type = Column(String(32), nullable=True)  # expense|revenue|vat|third_party|bank|cash
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisAccountingEngineProposal(Base):
    """Proposition comptable V2 — jamais d'écriture définitive."""

    __tablename__ = "elfis_accounting_engine_proposals"
    __table_args__ = (
        Index("ix_elfis_aep_org", "organization_id", "created_at"),
        Index("ix_elfis_aep_status", "organization_id", "status"),
        Index("ix_elfis_aep_source", "source_document_id"),
        UniqueConstraint(
            "organization_id",
            "source_document_id",
            "source_version",
            name="uq_elfis_aep_doc_ver",
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    status = Column(
        String(32), nullable=False, default=ProposalV2Status.DRAFT.value
    )
    direction = Column(String(32), nullable=False, default="purchase")
    document_type = Column(String(64), nullable=False, default="invoice")
    source_document_id = Column(String(64), nullable=True)  # invoice id or intake id
    source_kind = Column(String(32), nullable=True)  # invoice|intake|validated_data|manual
    source_version = Column(Integer, nullable=False, default=1)
    legacy_proposal_id = Column(String(36), nullable=True)  # lien V1 optionnel

    journal_code = Column(String(16), nullable=True)
    journal_label = Column(String(128), nullable=True)

    currency = Column(String(8), nullable=False, default="EUR")
    amount_ht = Column(Float, nullable=True)
    amount_vat = Column(Float, nullable=True)
    amount_ttc = Column(Float, nullable=True)
    vat_rate = Column(Float, nullable=True)

    lines_json = Column("lines", JSON, nullable=False, default=list)
    warnings_json = Column("warnings", JSON, nullable=False, default=list)
    errors_json = Column("errors", JSON, nullable=False, default=list)
    comments_json = Column("comments", JSON, nullable=False, default=list)
    explanations_json = Column("explanations", JSON, nullable=False, default=list)
    consistency_json = Column("consistency", JSON, nullable=False, default=dict)
    confidence_score = Column(Float, nullable=True)
    confidence_detail_json = Column("confidence_detail", JSON, nullable=False, default=dict)
    input_snapshot_json = Column("input_snapshot", JSON, nullable=False, default=dict)
    previous_snapshot_json = Column("previous_snapshot", JSON, nullable=True)

    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisAccountingLearningMemory(Base):
    """Mémoire d'apprentissage — validations utilisateur (pas de règles globales auto)."""

    __tablename__ = "elfis_accounting_learning_memory"
    __table_args__ = (
        Index("ix_elfis_alm_org_key", "organization_id", "memory_key"),
        UniqueConstraint(
            "organization_id", "memory_key", name="uq_elfis_alm_org_key"
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    memory_key = Column(String(255), nullable=False)  # hash direction+supplier+doc_type
    supplier_or_customer = Column(String(255), nullable=True)
    document_type = Column(String(64), nullable=True)
    direction = Column(String(32), nullable=True)
    preferred_expense_account = Column(String(16), nullable=True)
    preferred_revenue_account = Column(String(16), nullable=True)
    preferred_vat_account = Column(String(16), nullable=True)
    preferred_third_party_account = Column(String(16), nullable=True)
    preferred_journal = Column(String(16), nullable=True)
    vat_rate = Column(Float, nullable=True)
    hit_count = Column(Integer, nullable=False, default=1)
    source = Column(String(32), nullable=False, default="user_validation")
    payload_json = Column("payload", JSON, nullable=False, default=dict)
    last_used_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisAccountingEngineAudit(Base):
    __tablename__ = "elfis_accounting_engine_audit"
    __table_args__ = (Index("ix_elfis_aea_org", "organization_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    proposal_id = Column(String(36), nullable=True)
    action = Column(String(64), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    detail_json = Column("detail", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
