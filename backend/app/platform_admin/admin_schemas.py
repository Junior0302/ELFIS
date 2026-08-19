"""Schémas Platform Admin."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdminActionIn(BaseModel):
    reason: str = Field(..., min_length=3, max_length=2000)


class AdminIncidentNoteIn(BaseModel):
    note: str = Field(..., min_length=3, max_length=2000)


class AdminEntitlementOverrideIn(BaseModel):
    feature_code: str = Field(..., max_length=64)
    is_enabled: bool = True
    reason: str = Field(..., min_length=3, max_length=2000)


class AdminQuotaOverrideIn(BaseModel):
    quota_code: str = Field(..., max_length=64)
    limit_value: int | None = None
    reason: str = Field(..., min_length=3, max_length=2000)
