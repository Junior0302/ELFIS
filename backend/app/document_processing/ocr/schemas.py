"""Schémas API OCR (métadonnées uniquement — pas de texte dans les listes)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OCRResultOut(BaseModel):
    id: str
    document_id: str
    document_version_id: str
    organization_id: int
    processing_job_id: str | None = None
    provider_key: str
    provider_version: str
    status: str
    extraction_method: str
    page_count: int
    processed_page_count: int
    detected_languages: list[str] | None = Field(default=None, alias="detected_languages_json")
    average_confidence: float | None = None
    text_length: int
    requires_review: bool
    warnings: list[str] | None = Field(default=None, alias="warnings_json")
    error_code: str | None = None
    error_message_sanitized: str | None = None
    selection_reason_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # jamais object_key / texte

    model_config = {"from_attributes": True, "populate_by_name": True}


class OCRResultListOut(BaseModel):
    items: list[OCRResultOut]
    total: int
    limit: int
    offset: int


class OCRPageOut(BaseModel):
    id: str
    ocr_result_id: str
    page_number: int
    status: str
    character_count: int
    word_count: int | None = None
    confidence: float | None = None
    detected_language: str | None = None
    warnings: list[str] | None = Field(default=None, alias="warnings_json")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class OCRPageListOut(BaseModel):
    items: list[OCRPageOut]
    total: int


class OCRProvidersOut(BaseModel):
    items: list[dict[str, Any]]
