"""Sales Intelligence — Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceOut(BaseModel):
    type: str
    label: str
    value: str | int | float | None = None
    description: str | None = None
    source: str | None = None
    observed_at: datetime | None = None


class ExplanationOut(BaseModel):
    headline: str
    observed_facts: list[str] = Field(default_factory=list)
    rule_applied: str
    why_it_matters: str
    recommended_next_step: str
    resolution_condition: str


class InsightActionOut(BaseModel):
    action_type: str
    label: str
    route: str | None = None
    enabled: bool = True
    disabled_reason: str | None = None
    required_permission: str | None = None
    requires_confirmation: bool = False
    expected_resolution_behavior: str | None = None


class SalesFocusOut(BaseModel):
    title: str
    summary: str
    reason: str
    severity: str
    tone: str = "normal"  # urgent | important | normal | no_urgent_focus
    route: str | None = None
    action_label: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    evidence: list[Any] = Field(default_factory=list)
    insight_id: int | None = None
    generated_at: datetime


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    insight_type: str
    category: str
    severity: str
    priority_score: int
    title: str
    summary: str
    explanation: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Any] = Field(default_factory=list)
    recommended_action: dict[str, Any] = Field(default_factory=dict)
    available_actions: list[Any] = Field(default_factory=list)
    route: str | None = None
    source_type: str
    source_id: str | None = None
    source_label: str | None = None
    status: str
    linked_decision_id: str | None = None
    resolution_condition: str | None = None
    observed_value: str | None = None
    score: int | None = None
    first_detected_at: datetime
    last_detected_at: datetime
    resolved_at: datetime | None = None
    dismissed_at: datetime | None = None
    acknowledged_at: datetime | None = None


class InsightListOut(BaseModel):
    items: list[InsightOut]
    total: int
    page: int
    limit: int


class IntelligenceSummaryOut(BaseModel):
    active_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    opportunity_count: int = 0
    pipeline_count: int = 0
    proposal_count: int = 0
    task_count: int = 0
    acknowledged_count: int = 0


class IntelligenceOverviewOut(BaseModel):
    focus: SalesFocusOut
    summary: IntelligenceSummaryOut
    top_insights: list[InsightOut] = Field(default_factory=list)
    opportunity_insights: list[InsightOut] = Field(default_factory=list)
    pipeline_insights: list[InsightOut] = Field(default_factory=list)
    proposal_insights: list[InsightOut] = Field(default_factory=list)
    activity_insights: list[InsightOut] = Field(default_factory=list)
    counts: IntelligenceSummaryOut
    generated_at: datetime
    stale: bool = False


class DismissIn(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class SyncOut(BaseModel):
    created: int = 0
    updated: int = 0
    resolved: int = 0
    decisions_created: int = 0
    notifications_created: int = 0
    scanned_opportunities: int = 0
    scanned_proposals: int = 0
    scanned_tasks: int = 0
