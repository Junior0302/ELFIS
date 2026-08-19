"""Schémas API Smart Migration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StatusOut(BaseModel):
    migration_id: str
    smart_run_id: str | None = None
    status: str
    progress: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class DashboardOut(BaseModel):
    data: dict[str, Any]


class MetricsOut(BaseModel):
    data: dict[str, Any]


class ReportOut(BaseModel):
    data: dict[str, Any]


class ResumeOut(BaseModel):
    smart_run_id: str
    status: str
    progress_percent: float


class CancelOut(BaseModel):
    smart_run_id: str
    status: str


class RetryFailedOut(BaseModel):
    smart_run_id: str
    status: str


class RestartBatchIn(BaseModel):
    batch_id: str
    failed_only: bool = False


class RestartBatchOut(BaseModel):
    batch_id: str
    status: str
    progress_percent: float


class CleanupIn(BaseModel):
    action: str
    confirmed: bool = False
    migration_session_id: str | None = None


class StartIn(BaseModel):
    batch_size: int = 25
    max_workers: int = 4
    parallel: bool = False
    run_now: bool = True
