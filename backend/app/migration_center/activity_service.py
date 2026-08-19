"""MigrationActivityService — flux métier lisible (≠ Audit Engine)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.migration_center import metrics as mig_metrics
from app.migration_center.enums import ActivityActorType, ActivitySeverity, ActivityType
from app.migration_center.models import ElfisMigrationActivity

logger = logging.getLogger(__name__)

ACTIVITY_TITLES: dict[str, str] = {
    ActivityType.MIGRATION_CREATED.value: "Migration créée",
    ActivityType.PROFILE_SAVED.value: "Profil de l’entreprise enregistré",
    ActivityType.SOURCES_SAVED.value: "Sources de données sélectionnées",
    ActivityType.STEP_COMPLETED.value: "Étape complétée",
    ActivityType.MIGRATION_RESUMED.value: "Migration reprise",
    ActivityType.MIGRATION_CANCELLED.value: "Migration annulée",
    ActivityType.MIGRATION_CONFLICT_DETECTED.value: "Conflit de version détecté",
}


class MigrationActivityService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def record(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        activity_type: str,
        title: str | None = None,
        description: str | None = None,
        severity: str = ActivitySeverity.INFO.value,
        actor_type: str = ActivityActorType.SYSTEM.value,
        actor_user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        commit: bool = False,
    ) -> ElfisMigrationActivity:
        # Idempotence soft via metadata.idempotency_key
        if idempotency_key:
            existing = (
                self._db.query(ElfisMigrationActivity)
                .filter(ElfisMigrationActivity.organization_id == organization_id)
                .filter(ElfisMigrationActivity.migration_session_id == migration_session_id)
                .filter(ElfisMigrationActivity.activity_type == activity_type)
                .all()
            )
            for row in existing:
                meta = row.metadata_json or {}
                if meta.get("idempotency_key") == idempotency_key:
                    return row

        meta = dict(metadata or {})
        if idempotency_key:
            meta["idempotency_key"] = idempotency_key

        row = ElfisMigrationActivity(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            activity_type=activity_type,
            title=title or ACTIVITY_TITLES.get(activity_type, activity_type),
            description=description,
            severity=severity,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            metadata_json=meta,
            occurred_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        mig_metrics.incr("migration_activity_created_total")
        logger.info(
            "migration_activity_recorded",
            extra={
                "organization_id": organization_id,
                "migration_session_id": migration_session_id,
                "operation": "record_activity",
                "status": "ok",
                "activity_type": activity_type,
                "user_id": actor_user_id,
            },
        )
        return row

    def record_system_activity(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        activity_type: str,
        title: str | None = None,
        description: str | None = None,
        severity: str = ActivitySeverity.INFO.value,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        commit: bool = False,
    ) -> ElfisMigrationActivity:
        return self.record(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            activity_type=activity_type,
            title=title,
            description=description,
            severity=severity,
            actor_type=ActivityActorType.SYSTEM.value,
            metadata=metadata,
            idempotency_key=idempotency_key,
            commit=commit,
        )

    def record_user_activity(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        activity_type: str,
        actor_user_id: int | None,
        title: str | None = None,
        description: str | None = None,
        severity: str = ActivitySeverity.INFO.value,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        commit: bool = False,
    ) -> ElfisMigrationActivity:
        return self.record(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            activity_type=activity_type,
            title=title,
            description=description,
            severity=severity,
            actor_type=ActivityActorType.USER.value,
            actor_user_id=actor_user_id,
            metadata=metadata,
            idempotency_key=idempotency_key,
            commit=commit,
        )

    def list_for_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        limit: int = 50,
    ) -> list[ElfisMigrationActivity]:
        return (
            self._db.query(ElfisMigrationActivity)
            .filter(ElfisMigrationActivity.organization_id == organization_id)
            .filter(ElfisMigrationActivity.migration_session_id == migration_session_id)
            .order_by(ElfisMigrationActivity.occurred_at.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
