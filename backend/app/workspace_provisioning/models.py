"""Modèle d’état de provisioning — une ligne par organisation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WorkspaceProvisioningRun(Base):
    __tablename__ = "workspace_provisioning_runs"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_workspace_provisioning_org"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    current_step: Mapped[str] = mapped_column(String(64), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message_safe: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    provisioning_version: Mapped[int] = mapped_column(Integer, default=1)
