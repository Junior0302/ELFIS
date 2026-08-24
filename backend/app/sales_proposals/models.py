"""Commercial Proposal Engine V1 — SQLAlchemy models.

SalesPilot owns proposals. PDFs live in ELFIS Vault only.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


_JSON = JSON


class CommercialProposal(Base):
    __tablename__ = "sales_commercial_proposals"
    __table_args__ = (
        UniqueConstraint("organization_id", "proposal_number", name="uq_sales_proposal_org_number"),
        Index("ix_sales_proposal_org_status", "organization_id", "status"),
        Index("ix_sales_proposal_opportunity", "opportunity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_opportunities.id"), nullable=True, index=True
    )
    sales_company_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_companies.id"), nullable=True, index=True
    )
    person_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_people.id"), nullable=True
    )
    proposal_number: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_type: Mapped[str] = mapped_column(String(40), default="quote")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    linked_customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True
    )
    linked_invoice_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_documents.id"), nullable=True
    )
    reject_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reject_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # S1.6.1 conversion bridge
    conversion_status: Mapped[str] = mapped_column(String(32), default="not_ready")
    conversion_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conversion_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conversion_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conversion_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class CommercialProposalVersion(Base):
    __tablename__ = "sales_commercial_proposal_versions"
    __table_args__ = (
        UniqueConstraint("proposal_id", "version_number", name="uq_sales_proposal_version_num"),
        Index("ix_sales_proposal_version_org", "organization_id", "proposal_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    proposal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales_commercial_proposals.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Proposition commerciale")
    introduction: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    readiness_level: Mapped[str] = mapped_column(String(32), default="blocked")
    readiness_explanation: Mapped[dict] = mapped_column(_JSON, default=dict)
    pdf_vault_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vault_documents.id"), nullable=True
    )
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CommercialProposalLine(Base):
    __tablename__ = "sales_commercial_proposal_lines"
    __table_args__ = (Index("ix_sales_proposal_line_version", "proposal_version_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    proposal_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales_commercial_proposal_versions.id"), index=True
    )
    catalog_item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("catalog_items.id"), nullable=True
    )
    source_opportunity_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    discount_type: Mapped[str] = mapped_column(String(16), default="none")
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    metadata_json: Mapped[dict] = mapped_column("metadata", _JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CommercialProposalEvent(Base):
    """Append-only proposal timeline projection."""

    __tablename__ = "sales_commercial_proposal_events"
    __table_args__ = (Index("ix_sales_proposal_event_prop", "proposal_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    proposal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales_commercial_proposals.id"), index=True
    )
    version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(_JSON, default=dict)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class SalesProposalNumberSequence(Base):
    """Per-org yearly sequence for SP-{YEAR}-{SEQ}."""

    __tablename__ = "sales_proposal_number_sequences"
    __table_args__ = (
        UniqueConstraint("organization_id", "year", name="uq_sales_proposal_seq_org_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
