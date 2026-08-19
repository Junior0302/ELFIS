"""Schémas API Work Queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.decision_center.schemas import DecisionActionOut


class WaitingReasonOut(BaseModel):
    code: str
    label: str
    description: str | None = None
    retry_after: str | None = None


class WorkQueuePrimaryActionOut(BaseModel):
    action_type: str
    label: str
    method: Literal["NAVIGATE", "POST"] = "NAVIGATE"
    action_path: str | None = None
    endpoint: str | None = None
    enabled: bool = True


class WorkQueueItemOut(BaseModel):
    decision_id: str
    decision_type: str
    bucket: str
    status: str
    execution_status: str
    severity: str
    title: str
    summary: str
    source_type: str
    source_id: str
    created_at: datetime
    updated_at: datetime
    due_at: datetime | None = None
    age_label: str | None = None
    primary_action: WorkQueuePrimaryActionOut | None = None
    available_actions: list[DecisionActionOut] = Field(default_factory=list)
    is_blocking: bool = False
    waiting_reason: WaitingReasonOut | None = None
    last_activity: str | None = None
    progress_label: str | None = None
    required_permission: str | None = None
    evidence_summary: str | None = None
    started_at: datetime | None = None


class WorkQueueCountsOut(BaseModel):
    todo: int = 0
    in_progress: int = 0
    waiting: int = 0
    completed: int = 0


class WorkQueuePaginationOut(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class WorkQueueFiltersOut(BaseModel):
    bucket: str | None = None
    severity: str | None = None
    decision_type: str | None = None
    source_type: str | None = None
    search: str | None = None
    sort: str = "priority"


class WorkQueueOut(BaseModel):
    items: list[WorkQueueItemOut]
    pagination: WorkQueuePaginationOut
    counts: WorkQueueCountsOut
    filters: WorkQueueFiltersOut
    generated_at: datetime


class WorkQueueSummaryOut(BaseModel):
    """Sous-ensemble pour Command Center."""

    counts: WorkQueueCountsOut
    todo_insights: list[dict[str, Any]] = Field(default_factory=list)
