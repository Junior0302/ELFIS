"""Enums Smart Migration."""

from __future__ import annotations

from enum import Enum


class SmartRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RESUMING = "resuming"


class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class BatchItemStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class CleanupAction(str, Enum):
    ARCHIVE = "archive"
    PURGE_TEMP = "purge_temp"
    PURGE_JOBS = "purge_jobs"
    EXPIRE_SESSIONS = "expire_sessions"
    SECURE_DELETE = "secure_delete"


TERMINAL_BATCH = frozenset(
    {
        BatchStatus.COMPLETED.value,
        BatchStatus.CANCELLED.value,
    }
)

TERMINAL_ITEM = frozenset(
    {
        BatchItemStatus.COMPLETED.value,
        BatchItemStatus.SKIPPED.value,
        BatchItemStatus.CANCELLED.value,
    }
)

DEFAULT_BATCH_SIZE = 25
DEFAULT_MAX_WORKERS = 4
