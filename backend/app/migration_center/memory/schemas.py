"""Schémas Migration Memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_type: str
    key_hash: str = Field(min_length=8, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    scope: str = "session"
    source: str = "system"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str = "proposed"


class MemoryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    migration_session_id: str
    scope: str
    memory_type: str
    key_hash: str
    payload: dict[str, Any]
    confidence: float | None = None
    source: str
    status: str
    created_by_user_id: int | None = None
    validated_by_user_id: int | None = None
    validated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
