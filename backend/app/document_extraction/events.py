"""Événements Document Extraction."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_extraction.models import ElfisDocumentExtraction
from app.document_extraction.redaction import safe_event_payload
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames


def _map(event_type: str) -> str:
    return {
        "document.extraction.requested": EventNames.DOCUMENT_EXTRACTION_REQUESTED,
        "document.extraction.queued": EventNames.DOCUMENT_EXTRACTION_QUEUED,
        "document.extraction.started": EventNames.DOCUMENT_EXTRACTION_STARTED,
        "document.extraction.progressed": EventNames.DOCUMENT_EXTRACTION_PROGRESSED,
        "document.extraction.completed": EventNames.DOCUMENT_EXTRACTION_COMPLETED,
        "document.extraction.completed_with_warnings": EventNames.DOCUMENT_EXTRACTION_COMPLETED_WITH_WARNINGS,
        "document.extraction.failed": EventNames.DOCUMENT_EXTRACTION_FAILED,
        "document.extraction.cancelled": EventNames.DOCUMENT_EXTRACTION_CANCELLED,
        "document.extraction.awaiting_validation": EventNames.DOCUMENT_EXTRACTION_AWAITING_VALIDATION,
        "document.extraction.quota_exceeded": EventNames.DOCUMENT_EXTRACTION_QUOTA_EXCEEDED,
    }.get(event_type, event_type)


def publish_extraction_event(
    db: Session,
    *,
    event_type: str,
    extraction: ElfisDocumentExtraction,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    commit: bool = True,
) -> None:
    payload = safe_event_payload(
        {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "organization_id": extraction.organization_id,
            "migration_session_id": extraction.migration_session_id,
            "document_intake_item_id": extraction.document_intake_item_id,
            "universal_document_id": extraction.universal_document_id,
            "extraction_id": extraction.id,
            "status": extraction.status,
            "schema_name": extraction.schema_name,
            "schema_version": extraction.schema_version,
            "overall_confidence": extraction.overall_confidence,
            "requires_human_review": extraction.requires_human_review,
            "actor_user_id": actor_user_id,
            "occurred_at": datetime.utcnow().isoformat() + "Z",
            "schema_version_event": 1,
            "metadata": dict(metadata or {}),
        }
    )
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(extraction.organization_id),
            aggregate_type="document_extraction",
            aggregate_id=extraction.id,
            payload=payload,
            metadata={"source": "document_extraction"},
            correlation_id=uuid4(),
            idempotency_key=(
                idempotency_key
                or f"{event_type}:{extraction.organization_id}:{extraction.id}:{extraction.version}"
            )[:255],
        ),
        commit=commit,
    )
