"""Schémas Pydantic — Document Extraction."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractRequestIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    force_reextract: bool = False
    schema_name: str | None = None
    # Interdits côté client (ignorés si fournis) : provider, model, prompt, temperature, etc.

class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    universal_document_id: str | None = None
    migration_session_id: str | None = None
    schema_name: str
    schema_version: str
    extraction_version: str
    status: str
    strategy: str | None = None
    overall_confidence: float | None = None
    confidence_level: str | None = None
    critical_fields_confidence: float | None = None
    completeness_score: float | None = None
    consistency_score: float | None = None
    requires_human_review: bool = True
    structured_data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[Any] = Field(default_factory=list)
    errors: list[Any] = Field(default_factory=list)
    progress_percent: int = 0
    current_step: str | None = None
    text_source: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm_row(cls, row: Any, *, include_sensitive: bool = False) -> "ExtractionOut":
        data = dict(row.structured_data or {})
        if not include_sensitive:
            supplier = data.get("supplier")
            if isinstance(supplier, dict) and "iban" in supplier:
                supplier = dict(supplier)
                supplier.pop("iban", None)
                data["supplier"] = supplier
        return cls(
            id=row.id,
            document_id=row.document_intake_item_id,
            universal_document_id=row.universal_document_id,
            migration_session_id=row.migration_session_id,
            schema_name=row.schema_name,
            schema_version=row.schema_version,
            extraction_version=row.extraction_version,
            status=row.status,
            strategy=row.strategy,
            overall_confidence=row.overall_confidence,
            confidence_level=row.confidence_level,
            critical_fields_confidence=row.critical_fields_confidence,
            completeness_score=row.completeness_score,
            consistency_score=row.consistency_score,
            requires_human_review=row.requires_human_review,
            structured_data=data,
            warnings=list(row.warnings_json or []),
            errors=list(row.errors_json or []),
            progress_percent=row.progress_percent or 0,
            current_step=row.current_step,
            text_source=row.text_source,
            started_at=row.started_at,
            completed_at=row.completed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class ExtractionListOut(BaseModel):
    items: list[ExtractionOut]
    total: int


class ExtractionFieldsOut(BaseModel):
    fields: dict[str, Any]
    low_confidence: list[str] = Field(default_factory=list)


class ExtractionProvenanceOut(BaseModel):
    provenance: dict[str, Any]


class ExtractionWarningsOut(BaseModel):
    warnings: list[Any] = Field(default_factory=list)
    errors: list[Any] = Field(default_factory=list)


class ExtractBatchOut(BaseModel):
    extracted: int
    errors: list[dict[str, str]] = Field(default_factory=list)
    items: list[ExtractionOut] = Field(default_factory=list)
