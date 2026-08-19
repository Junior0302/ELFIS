"""Schémas Document Intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentExtractionOutput(BaseModel):
    text: str = ""
    page_count: Optional[int] = None
    language: Optional[str] = None
    quality_score: float = 0.0
    confidence: float = 0.0
    requires_ocr: bool = False
    requires_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class DocumentExtractionRequest(BaseModel):
    organization_id: int
    user_id: Optional[int] = None
    vault_document_id: str
    document_version: Optional[int] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None
    source_event_id: Optional[str] = None
    # Tests / injection interne uniquement
    content_bytes: Optional[bytes] = None


class DocumentExtractionResult(BaseModel):
    extraction_id: str
    vault_document_id: str
    status: str
    extractor_name: str
    text_length: int = 0
    quality_score: Optional[float] = None
    confidence: Optional[float] = None
    requires_ocr: bool = False
    requires_review: bool = False
    created: bool = True
    idempotent_reuse: bool = False
    job_id: Optional[str] = None


class DocumentExtractionView(BaseModel):
    extraction_id: str
    status: str
    extractor_name: str
    page_count: Optional[int] = None
    text_length: int = 0
    quality_score: Optional[float] = None
    confidence: Optional[float] = None
    requires_ocr: bool = False
    requires_review: bool = False
    language: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExtractTextAccepted(BaseModel):
    extraction_id: str
    job_id: Optional[str] = None
    status: str
    reused_existing_extraction: bool = False
