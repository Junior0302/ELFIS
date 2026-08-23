"""Types normalisés Banking Platform V1 — indépendants des fournisseurs."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConnectionStatus(str, Enum):
    preparing = "preparing"
    awaiting_consent = "awaiting_consent"
    connected = "connected"
    error = "error"
    disconnected = "disconnected"


class ConsentStartResult(BaseModel):
    """Résultat interne d’un parcours consentement — seul redirect_url sort vers le frontend."""

    model_config = ConfigDict(extra="forbid")

    redirect_url: str = Field(min_length=8, max_length=2048)


class ConsentCompleteResult(BaseModel):
    """Item fournisseur validé côté serveur après callback."""

    model_config = ConfigDict(extra="forbid")

    provider_connection_id: str = Field(min_length=1, max_length=128)
    bank_name: str = ""
    authentication_expires_at: str | None = None


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
    available_balance: float | None = None
    account_type: str = "other"
    balance_updated_at: datetime | None = None


class NormalizedTransaction(BaseModel):
    """Transaction normalisée — modèle unique quel que soit le fournisseur."""

    model_config = ConfigDict(extra="forbid")

    # Vide = pas d'identifiant provider. Ne jamais inventer un hash métier à la place.
    external_id: str = Field(default="", max_length=128)
    booked_at: date
    value_date: date | None = None
    label: str = Field(min_length=1, max_length=512)
    amount: float  # + crédit / - débit
    currency: str = "EUR"
    account_external_id: str = Field(min_length=1, max_length=128)
    category: str | None = None
    status: TransactionStatus = TransactionStatus.booked
    source: str = Field(min_length=1, max_length=32)  # provider d'origine
    counterparty_name: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=128)

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("label requis")
        return cleaned

    @field_validator("external_id")
    @classmethod
    def _clean_external_id(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("counterparty_name", "reference")
    @classmethod
    def _clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class TransactionPage(BaseModel):
    """Page fournisseur — ``next_cursor`` est opaque pour le domaine ELFIS."""

    model_config = ConfigDict(extra="forbid")

    transactions: list[NormalizedTransaction] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False


def optional_provider_float(raw: object | None) -> float | None:
    """Convertit une valeur fournisseur en float, ou None si absente / non numérique."""
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def optional_provider_date(raw: object | None) -> date | None:
    if raw is None or raw == "":
        return None
    text = str(raw).strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None


def optional_provider_datetime(raw: object | None) -> datetime | None:
    if raw is None or raw == "":
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


class ConnectorHealth(BaseModel):
    """État d'un fournisseur, indépendant de son implémentation."""

    provider: str
    configured: bool = False
    status: str = "unknown"  # ok | degraded | unavailable | not_configured
    message: str = ""
    latency_ms: int | None = None
