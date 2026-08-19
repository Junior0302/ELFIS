"""Types normalisés Banking Platform V1 — indépendants des fournisseurs."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConnectionStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class SyncType(str, Enum):
    initial = "initial"
    incremental = "incremental"


class SyncRunStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class TransactionStatus(str, Enum):
    booked = "booked"
    pending = "pending"


class NormalizedAccount(BaseModel):
    """Compte bancaire tel que retourné par n'importe quel connecteur."""

    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=128)
    label: str = "Compte courant"
    bank_name: str = ""
    iban: str = ""
    currency: str = "EUR"
    balance: float = 0.0


class NormalizedTransaction(BaseModel):
    """Transaction normalisée — modèle unique quel que soit le fournisseur."""

    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=128)
    booked_at: date
    label: str = Field(min_length=1, max_length=512)
    amount: float  # + crédit / - débit
    currency: str = "EUR"
    account_external_id: str = Field(min_length=1, max_length=128)
    category: str | None = None
    status: TransactionStatus = TransactionStatus.booked
    source: str = Field(min_length=1, max_length=32)  # provider d'origine

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("label requis")
        return cleaned


class ConnectorHealth(BaseModel):
    """État d'un fournisseur, indépendant de son implémentation."""

    provider: str
    configured: bool = False
    status: str = "unknown"  # ok | degraded | unavailable | not_configured
    message: str = ""
    latency_ms: int | None = None
