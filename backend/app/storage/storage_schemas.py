"""Schémas Pydantic — Document Registry (API)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StorageObjectOut(BaseModel):
    id: str
    provider: str
    namespace: str
    original_filename: str
    safe_filename: str
    mime_type_declared: str | None = None
    mime_type_detected: str | None = None
    extension: str | None = None
    size_bytes: int
    checksum_sha256: str | None = None
    status: str
    encryption_status: str
    created_at: datetime
    organization_id: int | None = None

    model_config = {"from_attributes": True}


class DocumentVersionOut(BaseModel):
    id: str
    document_id: str
    version_number: int
    storage_object_id: str
    status: str
    created_at: datetime
    created_by_user_id: int | None = None
    source: str
    change_reason: str | None = None
    original_filename: str
    size_bytes: int
    checksum_sha256: str | None = None
    mime_type: str | None = None
    superseded_at: datetime | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DocumentVersionListOut(BaseModel):
    items: list[DocumentVersionOut]
    total: int
    current_version_id: str | None = None


class DocumentRecordOut(BaseModel):
    id: str
    document_type: str
    title: str
    status: str
    organization_id: int
    product: str | None = None
    current_storage_object_id: str | None = None
    current_version_id: str | None = None
    version_count: int | None = None
    owner_user_id: int | None = None
    source: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    legal_hold_active: bool | None = None
    storage_object: StorageObjectOut | None = None
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DocumentListOut(BaseModel):
    items: list[DocumentRecordOut]
    total: int
    limit: int
    offset: int


class DocumentLinkCreate(BaseModel):
    entity_type: str
    entity_id: str
    relation_type: str = "attachment"


class DocumentLinkOut(BaseModel):
    id: str
    document_id: str
    entity_type: str
    entity_id: str
    relation_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentCreateMeta(BaseModel):
    title: str | None = None
    document_type: str = "file"
    product: str | None = None
    source: str = "upload"
    metadata: dict[str, Any] | None = None


class DocumentDeleteBody(BaseModel):
    reason: str | None = None


class LegalHoldCreate(BaseModel):
    reason: str
    reference: str | None = None
    metadata: dict[str, Any] | None = None


class LegalHoldOut(BaseModel):
    id: str
    document_id: str
    reason: str
    reference: str | None = None
    active: bool
    placed_at: datetime
    placed_by_user_id: int | None = None
    released_at: datetime | None = None
    released_by_user_id: int | None = None

    model_config = {"from_attributes": True}


class LegalHoldListOut(BaseModel):
    items: list[LegalHoldOut]
    total: int
