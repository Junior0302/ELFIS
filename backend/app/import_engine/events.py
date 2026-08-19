"""Événements Import Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.import_engine.models import ElfisImportRun


def _map(event_type: str) -> str:
    return {
        "import.started": EventNames.IMPORT_STARTED,
        "import.mapping.completed": EventNames.IMPORT_MAPPING_COMPLETED,
        "import.transaction.started": EventNames.IMPORT_TRANSACTION_STARTED,
        "import.transaction.committed": EventNames.IMPORT_TRANSACTION_COMMITTED,
        "import.completed": EventNames.IMPORT_COMPLETED,
        "import.failed": EventNames.IMPORT_FAILED,
        "rollback.started": EventNames.IMPORT_ROLLBACK_STARTED,
        "rollback.completed": EventNames.IMPORT_ROLLBACK_COMPLETED,
    }.get(event_type, event_type)


def publish_import_event(
    db: Session,
    *,
    event_type: str,
    run: ElfisImportRun,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": run.organization_id,
        "migration_session_id": run.migration_session_id,
        "document_intake_item_id": run.document_intake_item_id,
        "universal_document_id": run.universal_document_id,
        "import_run_id": run.id,
        "validation_session_id": run.validation_session_id,
        "status": run.status,
        "fingerprint": run.fingerprint,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "schema_version_event": 1,
        "metadata": {
            k: v
            for k, v in (metadata or {}).items()
            if k
            in {
                "error_code",
                "schema_name",
                "created_count",
                "linked_count",
                "duration_ms",
                "rollback_reason",
                "progress_percent",
            }
        },
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(run.organization_id),
            aggregate_type="import_engine",
            aggregate_id=run.id,
            payload=payload,
            metadata={"source": "import_engine"},
            correlation_id=uuid4(),
            idempotency_key=(
                f"{event_type}:{run.organization_id}:{run.id}:{run.version}:{run.status}"
            )[:255],
        ),
        commit=commit,
    )
