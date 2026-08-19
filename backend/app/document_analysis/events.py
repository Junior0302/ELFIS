"""Événements Document Analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_analysis.models import ElfisDocumentAnalysisReport
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames


def _map(event_type: str) -> str:
    return {
        "document.analysis.started": EventNames.DOCUMENT_ANALYSIS_STARTED,
        "document.analysis.completed": EventNames.DOCUMENT_ANALYSIS_COMPLETED,
        "document.analysis.failed": EventNames.DOCUMENT_ANALYSIS_FAILED,
        "document.analysis.ready_for_ai": EventNames.DOCUMENT_ANALYSIS_READY_FOR_AI,
    }.get(event_type, event_type)


def publish_analysis_event(
    db: Session,
    *,
    event_type: str,
    report: ElfisDocumentAnalysisReport,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    commit: bool = True,
) -> None:
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": report.organization_id,
        "migration_session_id": report.migration_session_id,
        "document_intake_item_id": report.document_intake_item_id,
        "universal_document_id": report.universal_document_id,
        "analysis_report_id": report.id,
        "status": report.status,
        "need_ocr": report.need_ocr,
        "classification_label": report.classification_label,
        "language_code": report.language_code,
        "quality_score": report.quality_score,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": 1,
        "metadata": dict(metadata or {}),
    }
    # Jamais de contenu fichier / chemin physique
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(report.organization_id),
            aggregate_type="document_analysis_report",
            aggregate_id=report.id,
            payload=payload,
            metadata={"source": "document_analysis"},
            correlation_id=uuid4(),
            idempotency_key=(
                idempotency_key
                or f"{event_type}:{report.organization_id}:{report.id}"
            )[:255],
        ),
        commit=commit,
    )
