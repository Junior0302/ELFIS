"""SalesPilot Pipeline Engine V1 — board schemas (backend-computed only)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PipelineMoveStageIn(BaseModel):
    stage_id: int
    """Target stage."""
    expected_stage_id: int | None = None
    """Current stage known by client — mismatch → 409 for rollback."""


class PipelineCardOut(BaseModel):
    id: int
    name: str
    company_id: int | None = None
    company_name: str | None = None
    estimated_amount: Decimal | None = None
    person_id: int | None = None
    contact_name: str | None = None
    owner_user_id: int | None = None
    owner_label: str | None = None
    probability: int
    priority: str
    source: str | None = None
    status: str
    stage_id: int
    stage_entered_at: datetime | None = None
    days_in_stage: int = 0
    aging_label: str
    last_activity_at: datetime | None = None
    last_activity_subject: str | None = None
    next_activity_at: datetime | None = None
    next_activity_subject: str | None = None
    health_score: int = 0
    health_label: str
    risk_level: str
    risk_label: str
    expected_close_date: date | None = None
    badges: list[str] = Field(default_factory=list)
    updated_at: datetime


class PipelineColumnOut(BaseModel):
    stage_id: int
    code: str
    name: str
    position: int
    probability: int
    is_won: bool
    is_lost: bool
    opportunity_count: int = 0
    amount_total: Decimal = Decimal("0")
    weighted_amount: Decimal = Decimal("0")
    average_probability: float = 0.0
    average_days_in_stage: float = 0.0
    cards: list[PipelineCardOut] = Field(default_factory=list)


class PipelineBoardSummaryOut(BaseModel):
    open_opportunities: int = 0
    pipeline_value: Decimal = Decimal("0")
    weighted_pipeline_value: Decimal = Decimal("0")
    won_count: int = 0
    lost_count: int = 0
    critical_count: int = 0


class PipelineBoardOut(BaseModel):
    pipeline_id: int
    pipeline_name: str
    pipeline_code: str
    stages: list[PipelineColumnOut] = Field(default_factory=list)
    summary: PipelineBoardSummaryOut
    generated_at: datetime


class PipelineDrawerActivityOut(BaseModel):
    id: int
    activity_type: str
    subject: str
    activity_at: datetime
    result: str | None = None


class PipelineDrawerTaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_at: datetime | None = None


class PipelineDrawerNoteOut(BaseModel):
    id: int
    body_markdown: str
    author_user_id: int | None = None
    created_at: datetime


class PipelineDrawerPersonOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None


class PipelineDrawerOut(BaseModel):
    opportunity: PipelineCardOut
    company_name: str | None = None
    contacts: list[PipelineDrawerPersonOut] = Field(default_factory=list)
    activities: list[PipelineDrawerActivityOut] = Field(default_factory=list)
    tasks: list[PipelineDrawerTaskOut] = Field(default_factory=list)
    notes: list[PipelineDrawerNoteOut] = Field(default_factory=list)
    stage_id: int
    stage_name: str
    amount: Decimal | None = None
    probability: int
    quick_actions: list[dict[str, str]] = Field(default_factory=list)
