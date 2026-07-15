from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ─── AUTH & ORGANISATION ─────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    firebase_uid: Mapped[str] = mapped_column(String(128), default="", index=True)
    phone: Mapped[str] = mapped_column(String(64), default="")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    legal_name: Mapped[str] = mapped_column(String(255), default="")
    siren: Mapped[str] = mapped_column(String(32), default="")
    vat_number: Mapped[str] = mapped_column(String(64), default="")
    country: Mapped[str] = mapped_column(String(8), default="FR")
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    logo: Mapped[str] = mapped_column(String(512), default="")
    industry: Mapped[str] = mapped_column(String(128), default="")
    subscription_plan: Mapped[str] = mapped_column(String(64), default="starter")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    permissions: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    description: Mapped[str] = mapped_column(String(255), default="")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    module: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(String(255), default="")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Company(Base):
    """Filiale / établissement sous une organisation."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    parent_company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(8), default="FR")
    currency: Mapped[str] = mapped_column(String(8), default="EUR")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    plan: Mapped[str] = mapped_column(String(64), default="starter")
    status: Mapped[str] = mapped_column(String(32), default="active")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AIAgent(Base):
    __tablename__ = "ai_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    status: Mapped[str] = mapped_column(String(32), default="active")


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(255))
    module: Mapped[str] = mapped_column(String(64), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ─── MODULE 4 — FACTURATION (clients / ventes) ───────────────────


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    vat_number: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SalesDocument(Base):
    """Devis / Facture / Avoir émis (Module 4)."""

    __tablename__ = "sales_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, default=1)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(32), default="facture")  # devis|facture|avoir
    number: Mapped[str] = mapped_column(String(64), index=True)
    issue_date: Mapped[str] = mapped_column(String(32))
    due_date: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    # draft | sent | accepted | refused | paid | partial | overdue | cancelled
    customer_name: Mapped[str] = mapped_column(String(255), default="")
    amount_ht: Mapped[float] = mapped_column(Float, default=0.0)
    amount_tva: Mapped[float] = mapped_column(Float, default=0.0)
    amount_ttc: Mapped[float] = mapped_column(Float, default=0.0)
    vat_rate: Mapped[float] = mapped_column(Float, default=20.0)
    lines_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    signature_status: Mapped[str] = mapped_column(String(32), default="none")  # none|pending|signed
    converted_from_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_documents.id"), index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    channel: Mapped[str] = mapped_column(String(32), default="email")
    message: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="sent")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_documents.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(64), default="virement")
    paid_at: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
