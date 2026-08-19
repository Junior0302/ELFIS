"""Schémas API Document Processing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProcessingJobCreate(BaseModel):
    document_id: str
    document_version_id: str | None = None
    pipeline_key: str | None = None
    product: str | None = None
    priority: int = 100
    idempotency_key: str | None = None
    metadata: dict[str, Any] | None = None


class ProcessingJobOut(BaseModel):
    id: str
    document_id: str
    document_version_id: str
    organization_id: int
    product: str | None = None
    pipeline_key: str
    status: str
    priority: int
    progress_percent: int
    current_step_key: str | None = None
    attempts_count: int
    max_attempts: int
    scheduled_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    cancelled_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message_sanitized: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ProcessingJobListOut(BaseModel):
    items: list[ProcessingJobOut]
    total: int
    limit: int
    offset: int


class ProcessingStepOut(BaseModel):
    id: str
    job_id: str
    step_key: str
    sequence_number: int
    status: str
    required: bool
    attempts_count: int
    max_attempts: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    next_retry_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message_sanitized: str | None = None
    output_summary: dict[str, Any] | None = Field(default=None, alias="output_summary_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ProcessingStepListOut(BaseModel):
    items: list[ProcessingStepOut]
    total: int


class ProcessingAttemptOut(BaseModel):
    id: str
    job_id: str
    step_id: str
    attempt_number: int
    worker_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_code: str | None = None
    error_message_sanitized: str | None = None
    retryable: bool

    model_config = {"from_attributes": True}


class ProcessingAttemptListOut(BaseModel):
    items: list[ProcessingAttemptOut]
    total: int
