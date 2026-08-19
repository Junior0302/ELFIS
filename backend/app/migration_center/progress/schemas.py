"""Schémas progression."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MigrationProgressPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    overall_percent: int = Field(ge=0, le=100, default=0)
    current_step: str = "welcome"
    current_step_percent: int = Field(ge=0, le=100, default=0)
    completed_steps: list[str] = Field(default_factory=list)
    pending_steps: list[str] = Field(default_factory=list)
    blocked_steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    estimated_remaining_seconds: int | None = None
    updated_at: datetime | None = None

    def to_storage(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        # Frontend ne doit jamais définir overall_percent — toujours backend
        data["estimated_remaining_seconds"] = None
        return data
