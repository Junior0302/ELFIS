"""Schémas Pydantic — Validation & Mapping."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FieldEditIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: Any = None
    action: str = "edit"  # edit|accept|reject
    reason: str | None = None


class RejectIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: str | None = None


class ResolveMatchIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resolution: str  # use_existing|create_later|ignore|unresolved


class ValidateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mark_ready: bool = True


class ValidationSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    universal_document_id: str | None = None
    extraction_id: str
    migration_session_id: str | None = None
    status: str
    validated_data: dict[str, Any] = Field(default_factory=dict)
    field_states: dict[str, str] = Field(default_factory=dict)
    warnings: list[Any] = Field(default_factory=list)
    errors: list[Any] = Field(default_factory=list)
    duplicate_summary: dict[str, Any] = Field(default_factory=dict)
    matching_summary: dict[str, Any] = Field(default_factory=dict)
    progress_percent: int = 0
    rejection_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm_row(cls, row: Any) -> "ValidationSessionOut":
        return cls(
            id=row.id,
            document_id=row.document_intake_item_id,
            universal_document_id=row.universal_document_id,
            extraction_id=row.extraction_id,
            migration_session_id=row.migration_session_id,
            status=row.status,
            validated_data=dict(row.validated_data or {}),
            field_states=dict(row.field_states or {}),
            warnings=list(row.warnings_json or []),
            errors=list(row.errors_json or []),
            duplicate_summary=dict(row.duplicate_summary or {}),
            matching_summary=dict(row.matching_summary or {}),
            progress_percent=row.progress_percent or 0,
            rejection_reason=row.rejection_reason,
            started_at=row.started_at,
            completed_at=row.completed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class ValidationSessionListOut(BaseModel):
    items: list[ValidationSessionOut]
    total: int


class ValidationFieldOut(BaseModel):
    field_path: str
    ai_value: Any = None
    current_value: Any = None
    status: str
    confidence: float | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    warnings: list[Any] = Field(default_factory=list)


class ValidationFieldsOut(BaseModel):
    fields: list[ValidationFieldOut]


class HistoryEntryOut(BaseModel):
    id: str
    field_path: str
    old_value: Any = None
    new_value: Any = None
    action: str
    reason: str | None = None
    actor_user_id: int | None = None
    created_at: datetime | None = None


class HistoryListOut(BaseModel):
    items: list[HistoryEntryOut]


class DuplicateOut(BaseModel):
    id: str
    other_document_id: str | None = None
    other_universal_document_id: str | None = None
    severity: str
    score: float
    matched_fields: list[str] = Field(default_factory=list)
    explanation: str | None = None
    resolution: str


class DuplicateListOut(BaseModel):
    items: list[DuplicateOut]


class MatchOut(BaseModel):
    id: str
    party_role: str
    category: str
    score: float
    contact_id: int | None = None
    contact_label: str | None = None
    matched_criteria: list[Any] = Field(default_factory=list)
    explanation: str | None = None
    resolution: str


class MatchListOut(BaseModel):
    items: list[MatchOut]


class BatchStartOut(BaseModel):
    started: int
    errors: list[dict[str, str]] = Field(default_factory=list)
    items: list[ValidationSessionOut] = Field(default_factory=list)
