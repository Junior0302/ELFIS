"""Schémas API classification."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClassificationOut(BaseModel):
    id: str
    document_id: str
    document_version_id: str
    processing_job_id: str | None = None
    organization_id: int
    classifier_key: str
    classifier_version: str
    predicted_type: str
    confidence_score: float
    status: str
    requires_review: bool
    evidence: list[dict[str, Any]] | None = Field(default=None, alias="evidence_json")
    alternatives: list[dict[str, Any]] | None = Field(default=None, alias="alternatives_json")
    source: str
    confirmed_type: str | None = None
    confirmed_by_user_id: int | None = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    # hint UI
    score_kind: str = "heuristic"

    model_config = {"from_attributes": True, "populate_by_name": True}


class ClassificationListOut(BaseModel):
    items: list[ClassificationOut]
    total: int
    limit: int
    offset: int


class ClassificationConfirmIn(BaseModel):
    confirmed_type: str


class ClassificationRejectIn(BaseModel):
    reason: str | None = None


class TaxonomyTypeOut(BaseModel):
    key: str
    label: str
    category: str
    description: str
    sensitive: bool
    processing_policy: str
    aliases: list[str]


class TaxonomyOut(BaseModel):
    items: list[TaxonomyTypeOut]
