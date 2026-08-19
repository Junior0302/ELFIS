"""Schémas API extraction — métadonnées uniquement dans les listes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExtractionResultOut(BaseModel):
    id: str
    organization_id: int
    document_id: str
    document_version_id: str
    processing_job_id: str | None = None
    ocr_result_id: str | None = None
    classification_id: str | None = None
    schema_key: str
    schema_version: str
    provider_key: str
    provider_version: str
    status: str
    confidence_score: float | None = None
    requires_review: bool
    fields_count: int
    valid_fields_count: int
    invalid_fields_count: int
    missing_required_fields_count: int
    validation_summary: dict[str, Any] | None = Field(default=None, alias="validation_summary_json")
    warnings: list[str] | None = Field(default=None, alias="warnings_json")
    error_code: str | None = None
    error_message_sanitized: str | None = None
    selection_reason_code: str | None = None
    source_reason_code: str | None = None
    effective_document_type: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ExtractionResultListOut(BaseModel):
    items: list[ExtractionResultOut]
    total: int
    limit: int
    offset: int


class ExtractedFieldOut(BaseModel):
    id: str
    extraction_result_id: str
    field_path: str
    field_type: str
    status: str
    display_value_masked: str | None = None
    confidence_score: float | None = None
    source_page: int | None = None
    evidence_reference: list[dict[str, Any]] | None = Field(
        default=None, alias="evidence_reference_json"
    )
    validation_codes: list[str] | None = Field(default=None, alias="validation_codes_json")
    manually_corrected: bool = False
    # normalized_value_json exposé seulement si non sensible (déjà filtré en DB)
    normalized_value: Any | None = Field(default=None, alias="normalized_value_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ExtractedFieldListOut(BaseModel):
    items: list[ExtractedFieldOut]
    total: int


class ExtractionConfirmIn(BaseModel):
    pass


class ExtractionRejectIn(BaseModel):
    reason: str | None = None


class ExtractionCorrectIn(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
