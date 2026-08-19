"""SalesPilot Dashboard V1 — response schemas (backend-computed KPIs only)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SalesDashboardSummaryOut(BaseModel):
    open_leads: int = 0
    open_opportunities: int = 0
    pipeline_value: Decimal = Decimal("0")
    weighted_pipeline_value: Decimal = Decimal("0")
    won_opportunities: int = 0
    lost_opportunities: int = 0
    overdue_tasks: int = 0
    activities_today: int = 0


class SalesPipelineStageOverviewOut(BaseModel):
    stage_id: int
    code: str
    name: str
    position: int
    probability: int
    is_won: bool
    is_lost: bool
    opportunity_count: int = 0
    amount_total: Decimal = Decimal("0")
    average_probability: float = 0.0


class SalesPipelineOverviewOut(BaseModel):
    pipeline_id: int
    pipeline_name: str
    stages: list[SalesPipelineStageOverviewOut] = Field(default_factory=list)


class SalesDashboardActivityOut(BaseModel):
    id: int
    activity_type: str
    subject: str
    activity_at: datetime
    bucket: str  # today | tomorrow | this_week
    result: str | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    owner_user_id: int | None = None


class SalesDashboardActivitiesOut(BaseModel):
    today: list[SalesDashboardActivityOut] = Field(default_factory=list)
    tomorrow: list[SalesDashboardActivityOut] = Field(default_factory=list)
    this_week: list[SalesDashboardActivityOut] = Field(default_factory=list)


class SalesDashboardTaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_at: datetime | None = None
    bucket: str  # overdue | today | upcoming
    assignee_user_id: int | None = None
    opportunity_id: int | None = None
    company_id: int | None = None


class SalesDashboardTasksOut(BaseModel):
    overdue: list[SalesDashboardTaskOut] = Field(default_factory=list)
    today: list[SalesDashboardTaskOut] = Field(default_factory=list)
    upcoming: list[SalesDashboardTaskOut] = Field(default_factory=list)


class SalesDashboardOpportunityOut(BaseModel):
    id: int
    name: str
    estimated_amount: Decimal | None = None
    probability: int
    stage_id: int
    stage_name: str | None = None
    status: str
    owner_user_id: int | None = None
    company_id: int | None = None
    company_name: str | None = None
    updated_at: datetime


class SalesQuickActionOut(BaseModel):
    id: str
    label: str
    description: str
    href: str


class SalesDashboardOut(BaseModel):
    summary: SalesDashboardSummaryOut
    pipeline: SalesPipelineOverviewOut | None = None
    activities: SalesDashboardActivitiesOut
    tasks: SalesDashboardTasksOut
    recent_opportunities: list[SalesDashboardOpportunityOut] = Field(default_factory=list)
    quick_actions: list[SalesQuickActionOut] = Field(default_factory=list)
    generated_at: datetime
