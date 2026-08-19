"""Types product integrations."""

from __future__ import annotations

from enum import Enum

PACKAGE_SCHEMA_V1 = "elfis_document_package_v1"
PACKAGE_SCHEMA_VERSION = "1"

PRODUCT_NOOP = "noop"
PRODUCT_COMPTAPILOT = "comptapilot"

BRIDGE_NOOP = "noop"
BRIDGE_COMPTAPILOT = "comptapilot"


class PackageStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    DELIVERY_PENDING = "delivery_pending"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    MANUAL_REVIEW = "manual_review"
    VALIDATED_NOT_DELIVERED = "validated_not_delivered"


BRIDGE_MODE_DISABLED = "disabled"
BRIDGE_MODE_DRY_RUN = "dry_run"
BRIDGE_MODE_LIVE = "live"


class AttemptStatus(str, Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
