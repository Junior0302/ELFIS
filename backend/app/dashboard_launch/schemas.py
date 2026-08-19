"""Schémas Launch Dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LaunchUserOut(BaseModel):
    display_name: str | None = None


class LaunchOrganizationOut(BaseModel):
    name: str


class LaunchStepOut(BaseModel):
    key: str
    label: str
    completed: bool
    action_path: str | None = None
    action_label: str | None = None


class LaunchRecommendedActionOut(BaseModel):
    key: str
    title: str
    description: str
    action_label: str
    action_path: str


class LaunchOnboardingOut(BaseModel):
    completed_steps: int
    total_steps: int
    progress: int
    steps: list[LaunchStepOut]
    recommended_action: LaunchRecommendedActionOut | None = None
    all_completed: bool = False


class LaunchQuickActionOut(BaseModel):
    key: str
    label: str
    description: str
    path: str
    enabled: bool = True


class LaunchActivityItemOut(BaseModel):
    id: str
    type: str
    title: str
    description: str
    occurred_at: datetime
    path: str | None = None


class LaunchDashboardOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_ready: bool
    user: LaunchUserOut
    organization: LaunchOrganizationOut
    onboarding: LaunchOnboardingOut
    quick_actions: list[LaunchQuickActionOut] = Field(default_factory=list)
    recent_activity: list[LaunchActivityItemOut] = Field(default_factory=list)


class AccountingDiscoveredOut(BaseModel):
    ok: bool = True
    accounting_discovery_completed: bool = True
