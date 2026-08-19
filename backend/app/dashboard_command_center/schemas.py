"""Schémas Command Center."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.dashboard_launch.schemas import LaunchActivityItemOut, LaunchQuickActionOut

Severity = Literal["critical", "high", "medium", "low"]
HealthStatus = Literal["ok", "warning", "critical", "degraded"]


class CommandPriorityOut(BaseModel):
    id: str
    severity: Severity
    title: str
    description: str
    action_path: str
    permission: str = ""


class CommandSummaryMetricOut(BaseModel):
    key: str
    label: str
    value: int | float
    unit: str | None = None
    path: str | None = None


class CommandSmartSummaryOut(BaseModel):
    headline: str
    metrics: list[CommandSummaryMetricOut] = Field(default_factory=list)
    has_financial_data: bool = False


class CommandAiInsightsOut(BaseModel):
    status: Literal["empty", "ready"] = "empty"
    message: str = "Aucune décision ne nécessite votre attention actuellement."
    insights: list[dict] = Field(default_factory=list)
    title: str = "À examiner"
    work_queue_path: str = "/work-queue"
    counts: dict[str, int] = Field(
        default_factory=lambda: {"todo": 0, "in_progress": 0, "waiting": 0, "completed": 0}
    )


class CommandHealthServiceOut(BaseModel):
    key: str
    label: str
    status: HealthStatus
    detail: str | None = None


class CommandSystemHealthOut(BaseModel):
    services: list[CommandHealthServiceOut] = Field(default_factory=list)


class CommandCenterOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_name: str
    priorities: list[CommandPriorityOut] = Field(default_factory=list)
    smart_summary: CommandSmartSummaryOut
    activity_timeline: list[LaunchActivityItemOut] = Field(default_factory=list)
    ai_insights: CommandAiInsightsOut = Field(default_factory=CommandAiInsightsOut)
    quick_actions: list[LaunchQuickActionOut] = Field(default_factory=list)
    system_health: CommandSystemHealthOut = Field(default_factory=CommandSystemHealthOut)
    generated_at: datetime
