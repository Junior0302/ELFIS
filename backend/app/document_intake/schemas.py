"""Schémas Pydantic — Document Intake Sprint 2.5."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IntakeItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    intake_token: str
    universal_document_id: str | None = None
    organization_id: int
    migration_session_id: str | None = None
    upload_session_id: str | None = None
    uploaded_by_user_id: int | None = None
    batch_id: str | None = None
    original_filename: str
    normalized_filename: str
    relative_path: str | None = None
    extension: str
    format_id: str
    declared_mime: str | None = None
    detected_mime: str | None = None
    detected_mime_type: str | None = None
    mime: str
    size_bytes: int
    checksum_sha256: str
    status: str
    lifecycle_status: str | None = None
    origin: str
    storage_provider: str | None = None
    is_duplicate: bool = False
    duplicate_of_id: str | None = None
    duplicate_type: str | None = None
    duplicate_of_item_id: str | None = None
    duplicate_confidence: float | None = None
    quarantine_reason: str | None = None
    reject_reason: str | None = None
    scan_verdict: str | None = None
    extract_later: bool = False
    preview_allowed: bool = False
    analysis_allowed: bool = False
    uploaded_at: datetime | None = None
    validated_at: datetime | None = None
    last_activity_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_orm_item(cls, item: Any) -> "IntakeItemOut":
        data = {
            "id": item.id,
            "intake_token": item.intake_token,
            "universal_document_id": getattr(item, "universal_document_id", None),
            "organization_id": item.organization_id,
            "migration_session_id": item.migration_session_id,
            "upload_session_id": getattr(item, "upload_session_id", None),
            "uploaded_by_user_id": item.uploaded_by_user_id,
            "batch_id": item.batch_id,
            "original_filename": item.original_filename,
            "normalized_filename": item.normalized_filename,
            "relative_path": item.relative_path,
            "extension": item.extension,
            "format_id": item.format_id,
            "declared_mime": item.declared_mime,
            "detected_mime": item.detected_mime,
            "detected_mime_type": item.detected_mime,
            "mime": item.mime,
            "size_bytes": item.size_bytes,
            "checksum_sha256": item.checksum_sha256,
            "status": item.status,
            "lifecycle_status": getattr(item, "lifecycle_status", None) or item.status,
            "origin": item.origin,
            "storage_provider": getattr(item, "storage_provider", None),
            "is_duplicate": item.is_duplicate,
            "duplicate_of_id": item.duplicate_of_id,
            "duplicate_type": getattr(item, "duplicate_type", None),
            "duplicate_of_item_id": getattr(item, "duplicate_of_item_id", None),
            "duplicate_confidence": getattr(item, "duplicate_confidence", None),
            "quarantine_reason": item.quarantine_reason,
            "reject_reason": item.reject_reason,
            "scan_verdict": item.scan_verdict,
            "extract_later": item.extract_later,
            "preview_allowed": item.preview_allowed,
            "analysis_allowed": item.analysis_allowed,
            "uploaded_at": item.uploaded_at,
            "validated_at": item.validated_at,
            "last_activity_at": getattr(item, "last_activity_at", None),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        return cls.model_validate(data)


class IntakeItemListOut(BaseModel):
    items: list[IntakeItemOut]
    total: int
    limit: int
    offset: int
    summary: dict[str, Any] = Field(default_factory=dict)


class FormatCatalogOut(BaseModel):
    items: list[dict[str, Any]]


class UploadResultOut(BaseModel):
    item: IntakeItemOut
    batch_id: str | None = None


class BatchUploadResultOut(BaseModel):
    batch_id: str
    items: list[IntakeItemOut]
    accepted: int
    rejected: int
    duplicates: int
    quarantined: int


class LifecycleEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    document_intake_item_id: str
    from_status: str | None = None
    to_status: str
    reason_code: str | None = None
    actor_type: str
    actor_user_id: int | None = None
    occurred_at: datetime | None = None
    created_at: datetime | None = None


class LifecycleListOut(BaseModel):
    items: list[LifecycleEntryOut]


class UploadSessionCreateIn(BaseModel):
    migration_session_id: str
    source_type: str = "manual"
    expected_file_count: int = 0
    expected_total_bytes: int = 0
    display_label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UploadSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    migration_session_id: str
    created_by_user_id: int
    status: str
    source_type: str
    display_label: str | None = None
    expected_file_count: int = 0
    received_file_count: int = 0
    validated_file_count: int = 0
    duplicate_file_count: int = 0
    rejected_file_count: int = 0
    cancelled_file_count: int = 0
    quarantined_file_count: int = 0
    expected_total_bytes: int = 0
    received_total_bytes: int = 0
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    expires_at: datetime | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Token technique — exposé uniquement comme référence interne
    internal_reference: str | None = None

    @classmethod
    def from_orm_session(cls, row: Any) -> "UploadSessionOut":
        return cls(
            id=row.id,
            organization_id=row.organization_id,
            migration_session_id=row.migration_session_id,
            created_by_user_id=row.created_by_user_id,
            status=row.status,
            source_type=row.source_type,
            display_label=row.display_label,
            expected_file_count=row.expected_file_count,
            received_file_count=row.received_file_count,
            validated_file_count=row.validated_file_count,
            duplicate_file_count=row.duplicate_file_count,
            rejected_file_count=row.rejected_file_count,
            cancelled_file_count=row.cancelled_file_count,
            quarantined_file_count=getattr(row, "quarantined_file_count", 0) or 0,
            expected_total_bytes=row.expected_total_bytes,
            received_total_bytes=row.received_total_bytes,
            started_at=row.started_at,
            last_activity_at=row.last_activity_at,
            completed_at=row.completed_at,
            cancelled_at=row.cancelled_at,
            expires_at=row.expires_at,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            internal_reference=row.upload_session_token,
        )


class UploadSessionListOut(BaseModel):
    items: list[UploadSessionOut]
    total: int
    limit: int
    offset: int


class UploadAnalyticsOut(BaseModel):
    schema_version: int = 1
    file_count: int = 0
    total_bytes: int = 0
    received_bytes: int = 0
    validated_count: int = 0
    duplicate_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    cancelled_count: int = 0
    average_upload_speed_bps: float | int | None = None
    duration_ms: int | None = None
    dominant_format: str | None = None
    format_distribution: dict[str, int] = Field(default_factory=dict)
    error_distribution: dict[str, int] = Field(default_factory=dict)
    completion_percent: int = 0
    updated_at: str | None = None
