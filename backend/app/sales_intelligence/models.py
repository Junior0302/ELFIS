"""Sales Intelligence — SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


_JSON = JSON


class SalesInsightItem(Base):
    __tablename__ = "sales_insight_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "deduplication_key", name="uq_sales_insight_org_dedupe"),
        Index("ix_sales_insight_org_status", "organization_id", "status"),
        Index("ix_sales_insight_org_category", "organization_id", "category"),
        Index("ix_sales_insight_org_severity", "organization_id", "severity"),
        Index("ix_sales_insight_org_source", "organization_id", "source_type", "source_id"),
        Index("ix_sales_insight_org_priority", "organization_id", "priority_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), index=True)
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deduplication_key: Mapped[str] = mapped_column(String(191), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation: Mapped[dict] = mapped_column(_JSON, default=dict)
    evidence: Mapped[list] = mapped_column(_JSON, default=list)
    recommended_action: Mapped[dict] = mapped_column(_JSON, default=dict)
    available_actions: Mapped[list] = mapped_column(_JSON, default=list)
    route: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolution_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    linked_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    observed_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dismiss_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    dismissed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
