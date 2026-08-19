"""Schémas API validation métier."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BusinessValidationOut(BaseModel):
    id: str
    organization_id: int
    document_id: str
    document_version_id: str
    extraction_result_id: str
    classification_id: str | None = None
    processing_job_id: str | None = None
    rule_set_key: str
    rule_set_version: str
    status: str
    valid: bool
    blocking_issue_count: int
    warning_count: int
    info_count: int
    requires_review: bool
    error_code: str | None = None
    error_message_sanitized: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BusinessValidationListOut(BaseModel):
    items: list[BusinessValidationOut]
    total: int
    limit: int
    offset: int


class ValidationIssueOut(BaseModel):
    id: str
    business_validation_id: str
    rule_key: str
    rule_version: str
    severity: str
    field_paths: list[str] | None = Field(default=None, alias="field_paths_json")
    issue_code: str
    message_code: str | None = None
    parameters: dict[str, Any] | None = Field(default=None, alias="parameters_json")
    blocking: bool
    resolved: bool
    resolution_type: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ValidationIssueListOut(BaseModel):
    items: list[ValidationIssueOut]
    total: int


class ResolveIssueIn(BaseModel):
    resolution_type: str
