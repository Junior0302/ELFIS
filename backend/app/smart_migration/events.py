"""Événements Smart Migration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.smart_migration.models import ElfisSmartMigrationRun


def _map(event_type: str) -> str:
    return {
        "migration.started": EventNames.SMART_MIGRATION_STARTED,
        "migration.progress": EventNames.SMART_MIGRATION_PROGRESS,
        "migration.completed": EventNames.SMART_MIGRATION_COMPLETED,
        "migration.failed": EventNames.SMART_MIGRATION_FAILED,
        "migration.cancelled": EventNames.SMART_MIGRATION_CANCELLED,
        "migration.resumed": EventNames.SMART_MIGRATION_RESUMED,
        "migration.report.ready": EventNames.SMART_MIGRATION_REPORT_READY,
    }.get(event_type, event_type)


def publish_smart_migration_event(
    db: Session,
    *,
    event_type: str,
    run: ElfisSmartMigrationRun,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    meta = metadata or {}
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": run.organization_id,
        "migration_id": run.migration_session_id,
        "smart_run_id": run.id,
        "correlation_id": run.correlation_id,
        "batch_id": meta.get("batch_id"),
        "document_id": meta.get("document_id"),
        "status": run.status,
        "progress_percent": run.progress_percent,
        "duration": meta.get("duration"),
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "schema_version_event": 1,
        "metadata": {
            k: v
            for k, v in meta.items()
            if k
            in {
                "batch_id",
                "document_id",
                "duration",
                "error_code",
                "report_id",
                "report_version",
            }
        },
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(run.organization_id),
            aggregate_type="smart_migration",
            aggregate_id=run.id,
            payload=payload,
            metadata={"source": "smart_migration"},
            correlation_id=uuid4(),
            idempotency_key=(
                f"{event_type}:{run.organization_id}:{run.id}:{run.version}:{run.status}"
            )[:255],
        ),
        commit=commit,
    )
