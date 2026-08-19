"""SalesPilot CRM Foundation V1 — SQLAlchemy models.

Naming: sales_* tables. SalesCompany ≠ models_saas.Company (filiale org).
Attachments reference Vault only (vault_document_id) — never store blobs.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class SalesOrgMixin:
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class SalesPipeline(Base, SalesOrgMixin):
    __tablename__ = "sales_pipelines"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_sales_pipeline_org_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    stages: Mapped[list[SalesPipelineStage]] = relationship(
        "SalesPipelineStage",
        back_populates="pipeline",
        order_by="SalesPipelineStage.position",
    )


class SalesPipelineStage(Base, SalesOrgMixin):
    __tablename__ = "sales_pipeline_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "code", name="uq_sales_stage_pipeline_code"),
        Index("ix_sales_stage_pipeline_pos", "pipeline_id", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_pipelines.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    probability: Mapped[int] = mapped_column(Integer, default=0)  # 0–100
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    pipeline: Mapped[SalesPipeline] = relationship("SalesPipeline", back_populates="stages")


class SalesLostReason(Base, SalesOrgMixin):
    __tablename__ = "sales_lost_reasons"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_sales_lost_org_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SalesWinReason(Base, SalesOrgMixin):
    __tablename__ = "sales_win_reasons"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_sales_win_org_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SalesTag(Base, SalesOrgMixin):
    __tablename__ = "sales_tags"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_sales_tag_org_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(32), default="#64748b")


class SalesTagLink(Base):
    """Polymorphic tag assignment — entity_type: lead|company|person|opportunity|task|activity."""

    __tablename__ = "sales_tag_links"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "tag_id",
            "entity_type",
            "entity_id",
            name="uq_sales_tag_link",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_tags.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


class SalesCompany(Base, SalesOrgMixin):
    """CRM account / company — not models_saas.Company."""

    __tablename__ = "sales_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    trade_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    siret: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address_line: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|inactive
    notes_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Future ComptaPilot / Contact bridge (optional)
    linked_contact_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("contacts.id"), nullable=True)
    linked_customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True, index=True
    )


class SalesPerson(Base, SalesOrgMixin):
    __tablename__ = "sales_people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_companies.id"), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    linked_contact_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("contacts.id"), nullable=True)


class SalesLead(Base, SalesOrgMixin):
    __tablename__ = "sales_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    # new|contacted|qualified|unqualified|converted
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_companies.id"), nullable=True)
    person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_people.id"), nullable=True)
    # Set after opportunity create — no FK to avoid circular dependency with sales_opportunities.lead_id
    converted_opportunity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesOpportunity(Base, SalesOrgMixin):
    __tablename__ = "sales_opportunities"
    __table_args__ = (Index("ix_sales_opp_org_stage", "organization_id", "stage_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    probability: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_pipelines.id"), index=True)
    stage_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_pipeline_stages.id"), index=True)
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_companies.id"), nullable=True, index=True)
    person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_people.id"), nullable=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_leads.id"), nullable=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    # open|won|lost|abandoned
    lost_reason_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_lost_reasons.id"), nullable=True)
    win_reason_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_win_reasons.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Relation préparée vers devis ComptaPilot (SalesDocument) — pas d'Invoice ici
    quote_document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_documents.id"), nullable=True
    )
    # Set when entering current stage (aging / avg time in stage)
    stage_entered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    # Hybrid amount mode (S1.6) — calculated from products vs manual/override
    calculated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    final_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    amount_mode: Mapped[str] = mapped_column(String(32), default="calculated")
    # calculated|manual|hybrid_override
    amount_difference: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    amount_override_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_override_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


PARTICIPANT_ROLES = (
    "decision_maker",
    "influencer",
    "technical",
    "buyer",
    "primary",
)


class SalesOpportunityParticipant(Base, SalesOrgMixin):
    """Buying-center roles on a deal — prepared multi-role support."""

    __tablename__ = "sales_opportunity_participants"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "opportunity_id",
            "person_id",
            "role",
            name="uq_sales_opp_participant_role",
        ),
        Index("ix_sales_opp_participant_opp", "opportunity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_opportunities.id"), index=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_people.id"), index=True)
    # decision_maker|influencer|technical|buyer|primary
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class SalesOpportunityProduct(Base, SalesOrgMixin):
    """Deal line items — totals computed server-side. Not a quote engine."""

    __tablename__ = "sales_opportunity_products"
    __table_args__ = (Index("ix_sales_opp_product_opp", "opportunity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_opportunities.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    # Remise en pourcentage 0–100
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    # Total ligne stocké (source de vérité backend)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    position: Mapped[int] = mapped_column(Integer, default=0)


class SalesActivity(Base, SalesOrgMixin):
    __tablename__ = "sales_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # call|email|meeting|visit|task|note
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    result: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_opportunities.id"), nullable=True, index=True
    )
    company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_companies.id"), nullable=True)
    person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_people.id"), nullable=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_leads.id"), nullable=True)


class SalesTask(Base, SalesOrgMixin):
    __tablename__ = "sales_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="todo", index=True)
    # todo|in_progress|done|cancelled
    assignee_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    opportunity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sales_opportunities.id"), nullable=True, index=True
    )
    company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_companies.id"), nullable=True)
    person_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sales_people.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SalesNote(Base, SalesOrgMixin):
    __tablename__ = "sales_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


class SalesAttachment(Base, SalesOrgMixin):
    """Vault reference only — never store file bytes here."""

    __tablename__ = "sales_attachments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "vault_document_id",
            "entity_type",
            "entity_id",
            name="uq_sales_attachment_vault",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vault_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("vault_documents.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
