"""Schémas Pydantic — Job Queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobRequest(BaseModel):
    job_name: str
    job_version: int = 1
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    queue_name: str = "default"
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    max_attempts: int = 5
    scheduled_at: Optional[datetime] = None
    timeout_seconds: Optional[int] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_event_id: Optional[str] = None
    parent_job_id: Optional[str] = None


class JobResult(BaseModel):
    job_id: str
    created: bool
    status: str
    queue_name: str
    scheduled_at: Optional[datetime] = None
    idempotent_reuse: bool = False


class JobExecutionResult(BaseModel):
    status: str = "completed"
    result: Optional[dict[str, Any]] = None
    progress: int = 100
    message: Optional[str] = None


class JobUserView(BaseModel):
    job_id: str
    job_name: str
    status: str
    progress: int
    progress_message: Optional[str] = None
    attempt_count: int
    max_attempts: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None


class JobAttemptView(BaseModel):
    attempt_number: int
    worker_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class JobPlatformListItem(BaseModel):
    job_id: str
    job_name: str
    job_version: int
    queue_name: str
    status: str
    priority: int
    progress: int
    progress_message: Optional[str] = None
    attempt_count: int
    max_attempts: int
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    locked_by: Optional[str] = None
    available_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobPlatformDetail(JobPlatformListItem):
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[dict[str, Any]] = None
    last_error: Optional[str] = None
    timeout_seconds: Optional[int] = None
    idempotency_key: Optional[str] = None
    causation_event_id: Optional[str] = None
    parent_job_id: Optional[str] = None


class JobListResponse(BaseModel):
    items: list[JobPlatformListItem]
    total: int
    page: int
    page_size: int
