"""Modèles Banking Platform V1 — connexions bancaires et journal de synchronisation.

Les comptes et transactions restent stockés dans ``BankAccount`` / ``BankTransaction``
(app.models) : le Banking Engine est l'unique source de vérité, ces tables
sont simplement enrichies (provider, connection_id, status, source).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ElfisBankConnection(Base):
    """Connexion à une banque via un fournisseur (demo, bridge, powens…)."""

    __tablename__ = "elfis_bank_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    provider_connection_id: Mapped[str] = mapped_column(String(128), default="")
    bank_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="connected", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisBankSyncRun(Base):
    """Journal d'une synchronisation (audit + reprise après erreur)."""

    __tablename__ = "elfis_bank_sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    connection_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    sync_type: Mapped[str] = mapped_column(String(16), default="initial")  # initial | incremental
    trigger: Mapped[str] = mapped_column(String(16), default="manual")  # manual | scheduled | retry
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)
    accounts_synced: Mapped[int] = mapped_column(Integer, default=0)
    transactions_created: Mapped[int] = mapped_column(Integer, default=0)
    transactions_updated: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    # Curseur de reprise : dernière date comptabilisée avec succès (ISO YYYY-MM-DD)
    cursor: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resumed_from_cursor: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), default=_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
