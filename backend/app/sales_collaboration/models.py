"""SalesPilot Collaboration V1 — models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class SalesTeam(Base):
    __tablename__ = "sales_teams"
    __table_args__ = (Index("ix_sales_team_org", "organization_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|archived
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SalesTeamMember(Base):
    __tablename__ = "sales_team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_sales_team_member"),
        Index("ix_sales_team_member_user", "organization_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_teams.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(40), default="member")  # lead|manager|member|viewer
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SalesComment(Base):
    __tablename__ = "sales_comments"
    __table_args__ = (
        Index("ix_sales_comment_entity", "organization_id", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list] = mapped_column(JSON, default=list)  # [{user_id, label}]
    vault_document_ids: Mapped[list] = mapped_column(JSON, default=list)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SalesFollower(Base):
    __tablename__ = "sales_followers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "entity_type", "entity_id", "user_id", name="uq_sales_follower"
        ),
        Index("ix_sales_follower_user", "organization_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SalesReviewRequest(Base):
    __tablename__ = "sales_review_requests"
    __table_args__ = (
        Index("ix_sales_review_entity", "organization_id", "entity_type", "entity_id"),
        Index("ix_sales_review_reviewer", "organization_id", "reviewer_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    requester_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending|approved|changes_requested|rejected
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SalesOwnershipTransfer(Base):
    __tablename__ = "sales_ownership_transfers"
    __table_args__ = (
        Index("ix_sales_transfer_entity", "organization_id", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    to_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
