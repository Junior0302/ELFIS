"""Schémas Pydantic — Import Engine API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.import_engine.models import ElfisImportReport, ElfisImportRun


class ImportRunOut(BaseModel):
    id: str
    document_id: str
    universal_document_id: str | None = None
    validation_session_id: str
    validation_version: int
    migration_session_id: str | None = None
    schema_name: str | None = None
    status: str
    fingerprint: str
    progress_percent: int
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[Any] = Field(default_factory=list)
    created_objects: list[Any] = Field(default_factory=list)
    linked_objects: list[Any] = Field(default_factory=list)
    report_id: str | None = None
    duration_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rolled_back_at: datetime | None = None
    rollback_reason: str | None = None
    actor_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm_row(cls, row: ElfisImportRun) -> ImportRunOut:
        return cls(
            id=row.id,
            document_id=row.document_intake_item_id,
            universal_document_id=row.universal_document_id,
            validation_session_id=row.validation_session_id,
            validation_version=int(row.validation_version or 1),
            migration_session_id=row.migration_session_id,
            schema_name=row.schema_name,
            status=row.status,
            fingerprint=row.fingerprint,
            progress_percent=int(row.progress_percent or 0),
            error_code=row.error_code,
            error_message=row.error_message,
            warnings=list(row.warnings_json or []),
            created_objects=list(row.created_objects_json or []),
            linked_objects=list(row.linked_objects_json or []),
            report_id=row.report_id,
            duration_ms=row.duration_ms,
            started_at=row.started_at,
            completed_at=row.completed_at,
            rolled_back_at=row.rolled_back_at,
            rollback_reason=row.rollback_reason,
            actor_user_id=row.actor_user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class ImportRunListOut(BaseModel):
    items: list[ImportRunOut]
    total: int


class ImportReportOut(BaseModel):
    id: str
    import_run_id: str
    version: int
    documents: list[Any] = Field(default_factory=list)
    created_objects: list[Any] = Field(default_factory=list)
    linked_objects: list[Any] = Field(default_factory=list)
    warnings: list[Any] = Field(default_factory=list)
    duration_ms: int | None = None
    actor_user_id: int | None = None
    report: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @classmethod
    def from_orm_row(cls, row: ElfisImportReport) -> ImportReportOut:
        return cls(
            id=row.id,
            import_run_id=row.import_run_id,
            version=int(row.version or 1),
            documents=list(row.documents_json or []),
            created_objects=list(row.created_objects_json or []),
            linked_objects=list(row.linked_objects_json or []),
            warnings=list(row.warnings_json or []),
            duration_ms=row.duration_ms,
            actor_user_id=row.actor_user_id,
            report=dict(row.report_json or {}),
            created_at=row.created_at,
        )


class RollbackIn(BaseModel):
    reason: str | None = "manual"


class ReadyDocumentOut(BaseModel):
    document_id: str
    universal_document_id: str | None = None
    validation_session_id: str
    validation_version: int
    schema_name: str | None = None
    status: str
    already_imported: bool = False


class ReadyDocumentListOut(BaseModel):
    items: list[ReadyDocumentOut]
    total: int
