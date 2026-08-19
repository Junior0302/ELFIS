"""Schemas API Accounting Intelligence V2."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecommendQuery(BaseModel):
    payload: dict[str, Any] | None = None
    proposal_id: str | None = None
    generate_proposal: bool = False


class FeedbackIn(BaseModel):
    action: str = Field(..., description="accept|modify|reject")
    recommendation_id: str | None = None
    proposal_id: str | None = None
    validation_seconds: float | None = None
    comment: str | None = None
    modifications: dict[str, Any] | None = None
    cancelled: bool = False
    import_rejected: bool = False


class RetrainIn(BaseModel):
    note: str | None = None


class SimilarityIn(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    limit: int = 5


class IntelligenceOut(BaseModel):
    data: dict[str, Any]
