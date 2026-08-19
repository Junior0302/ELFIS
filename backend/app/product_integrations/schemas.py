"""Schémas API product integrations — métadonnées seulement (pas de payload)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PackageOut(BaseModel):
    id: str
    organization_id: int
    product_key: str
    document_id: str
    document_version_id: str
    classification_id: str | None = None
    ocr_result_id: str | None = None
    extraction_result_id: str
    business_validation_id: str
    package_schema_key: str
    package_schema_version: str
    status: str
    checksum_sha256: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PackageListOut(BaseModel):
    items: list[PackageOut]
    total: int
    limit: int
    offset: int


class PackageCreateIn(BaseModel):
    document_id: str
    document_version_id: str | None = None
    business_validation_id: str | None = None


class DeliveryOut(BaseModel):
    id: str
    organization_id: int
    package_id: str
    product_key: str
    bridge_key: str
    bridge_version: str
    status: str
    attempt_count: int
    max_attempts: int
    external_reference: str | None = None
    last_error_code: str | None = None
    last_error_message_sanitized: str | None = None
    next_retry_at: datetime | None = None
    started_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryListOut(BaseModel):
    items: list[DeliveryOut]
    total: int
    limit: int
    offset: int


class BridgesOut(BaseModel):
    items: list[dict]
