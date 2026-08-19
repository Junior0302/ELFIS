"""Sales Operations V1 — Saved Views model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class SalesSavedView(Base):
    __tablename__ = "sales_saved_views"
    __table_args__ = (
        UniqueConstraint("organization_id", "owner_user_id", "name", "resource", name="uq_sales_saved_view"),
        Index("ix_sales_saved_view_org_resource", "organization_id", "resource"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    resource: Mapped[str] = mapped_column(String(40), nullable=False)  # leads|companies|people|opportunities|tasks|activities|proposals
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    sort: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
