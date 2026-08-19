"""Schémas Pydantic — Document Analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    document_intake_item_id: str
    universal_document_id: str | None = None
    migration_session_id: str | None = None
    status: str
    schema_version: int = 1
    analysis_version: str
    need_ocr: bool | None = None
    classification_label: str | None = None
    classification_confidence: float | None = None
    language_code: str | None = None
    language_confidence: float | None = None
    quality_score: int | None = None
    orientation_degrees: int | None = None
    page_count: int | None = None
    detected_format: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    processing_time_ms: int | None = None
    current_step: str | None = None
    steps_completed: int = 0
    steps_total: int = 12
    progress_percent: int = 0
    report: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm_report(cls, row: Any) -> "AnalysisReportOut":
        steps_total = max(1, int(getattr(row, "steps_total", 12) or 12))
        steps_done = int(getattr(row, "steps_completed", 0) or 0)
        pct = min(100, int(round(100.0 * steps_done / steps_total)))
        if row.status == "completed":
            pct = 100
        return cls(
            id=row.id,
            organization_id=row.organization_id,
            document_intake_item_id=row.document_intake_item_id,
            universal_document_id=row.universal_document_id,
            migration_session_id=row.migration_session_id,
            status=row.status,
            schema_version=row.schema_version,
            analysis_version=row.analysis_version,
            need_ocr=row.need_ocr,
            classification_label=row.classification_label,
            classification_confidence=row.classification_confidence,
            language_code=row.language_code,
            language_confidence=row.language_confidence,
            quality_score=row.quality_score,
            orientation_degrees=row.orientation_degrees,
            page_count=row.page_count,
            detected_format=row.detected_format,
            warnings=list(row.warnings_json or []),
            error_code=row.error_code,
            error_message=row.error_message,
            processing_time_ms=row.processing_time_ms,
            current_step=row.current_step,
            steps_completed=steps_done,
            steps_total=steps_total,
            progress_percent=pct,
            report=dict(row.report_json or {}),
            started_at=row.started_at,
            completed_at=row.completed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class AnalysisReportListOut(BaseModel):
    items: list[AnalysisReportOut]
    total: int
    limit: int
    offset: int


class AnalyzeBatchOut(BaseModel):
    analyzed: int
    errors: list[dict[str, str]] = Field(default_factory=list)
    items: list[AnalysisReportOut] = Field(default_factory=list)


class AnalyzeItemIn(BaseModel):
    force: bool = False
