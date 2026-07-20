"""Schémas métier Event Bus (DomainEvent, statuts)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    retry = "retry"
    failed = "failed"
    dead_letter = "dead_letter"
    cancelled = "cancelled"


class DeliveryStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    retry = "retry"
    failed = "failed"
    dead_letter = "dead_letter"
    skipped = "skipped"


FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "pdf",
        "pdf_bytes",
        "content",
        "file_content",
        "attachment_content",
        "api_key",
        "service_role_key",
        "jwt",
        "token",
        "password",
        "signed_url",
        "download_url",
        "authorization",
        "brevo_api_key",
        "email_body",
        "message_body",
        "iban",
        "bic",
    }
)


class DomainEvent(BaseModel):
    """Événement métier strict — payload sans secrets ni PDF."""

    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_name: str
    event_version: int = 1
    organization_id: int
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    causation_id: uuid.UUID | None = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("event_name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("event_name requis")
        return cleaned

    @field_validator("payload", "metadata")
    @classmethod
    def _no_forbidden_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("doit être un objet JSON")
        lowered = {str(k).lower() for k in value}
        bad = lowered & FORBIDDEN_PAYLOAD_KEYS
        if bad:
            raise ValueError(f"clés interdites dans payload/metadata: {sorted(bad)}")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def _clean_idempotency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned[:255] if cleaned else None


class EventListItem(BaseModel):
    id: str
    event_id: str
    event_name: str
    organization_id: int
    status: str
    attempt_count: int
    max_attempts: int
    available_at: datetime | None = None
    processed_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime | None = None
