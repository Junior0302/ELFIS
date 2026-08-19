from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FiscalPeriodRecord(Base):
    """Clôture / déclaration TVA manuelle (MVP commercial — pas de verrouillage écritures)."""

    __tablename__ = "fiscal_period_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "period_key",
            "kind",
            name="uq_fiscal_period_org_key_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    period_key: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM
    kind: Mapped[str] = mapped_column(String(32), index=True)
    # vat_declaration | period_close
    status: Mapped[str] = mapped_column(String(32), default="closed")
    notes: Mapped[str] = mapped_column(Text, default="")
    closed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
