"""Contexte + résultat d'étape."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.document_processing.models import (
    ElfisDocumentProcessingJob,
    ElfisDocumentProcessingStep,
)
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject


@dataclass
class ProcessingStepResult:
    success: bool
    status: str = "completed"  # completed | failed | skipped | blocked
    output_summary: dict[str, Any] | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    retryable: bool = False
    error_code: str | None = None
    error_message_sanitized: str | None = None


@dataclass
class ProcessingContext:
    db: Session
    job: ElfisDocumentProcessingJob
    step: ElfisDocumentProcessingStep
    document: ElfisDocumentRecord
    version: ElfisDocumentVersion
    storage_object: ElfisStorageObject | None
    worker_id: str
    cancellation_requested: bool = False
