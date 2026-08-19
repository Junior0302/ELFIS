"""Schémas Pydantic Billing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    plan_code: str = Field(default="starter", max_length=64)
    automatic_renewal_accepted: bool = False
    terms_accepted: bool = False


class CancelRequest(BaseModel):
    at_period_end: bool = True


class EntitlementOverrideIn(BaseModel):
    feature_code: str = Field(..., max_length=64)
    is_enabled: bool
    ends_at: datetime | None = None
    value: dict[str, Any] | None = None


class ChangePlanIn(BaseModel):
    plan_code: str = Field(..., max_length=64)


class PlanUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    price_amount: float | None = None
    trial_days: int | None = None
    is_active: bool | None = None
    is_public: bool | None = None
    features: dict[str, bool] | None = None
    quotas: dict[str, int | None] | None = None
    stripe_price_id: str | None = None


class QuotaCheckResult(BaseModel):
    allowed: bool
    quota_code: str
    limit_value: int | None = None
    used_value: int = 0
    remaining_value: int | None = None
    period_started_at: datetime | None = None
    period_ends_at: datetime | None = None
    hard_limit: bool = True
