"""Service métier — Assistant de Migration (architecture stage 2)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.migration_center import metrics as mig_metrics
from app.migration_center.activity_service import MigrationActivityService
from app.migration_center.enums import (
    ALLOWED_TRANSITIONS,
    CANCELABLE_STATUSES,
    STATUS_TO_STEP,
    STEP_PROFILE,
    STEP_SOURCES,
    STEP_WELCOME,
    ActivitySeverity,
    ActivityType,
    MigrationMode,
    MigrationSessionStatus,
    TimelineStepKey,
)
from app.migration_center.events import publish_migration_event
from app.migration_center.exceptions import (
    MigrationConflictError,
    MigrationNotFoundError,
    MigrationValidationError,
)
from app.migration_center.models import ElfisMigrationSession
from app.migration_center.profile_utils import (
    empty_profile_envelope,
    new_session_token,
    unwrap_company_profile,
    wrap_company_profile,
)
from app.migration_center.progress.service import MigrationProgressService
from app.migration_center.repository import MigrationCenterRepository
from app.migration_center.schemas import CompanyProfileIn
from app.migration_center.source_registry import list_source_catalog, validate_selected_sources
from app.migration_center.timeline_service import MigrationTimelineService

logger = logging.getLogger(__name__)


class MigrationCenterService:
    def __init__(self, db: Session, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = MigrationCenterRepository(db)
        self._audit = audit_logger
        self._timeline = MigrationTimelineService(db)
        self._activity = MigrationActivityService(db)
        self._progress = MigrationProgressService()

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            fn = getattr(self._audit, method, None)
            if callable(fn):
                fn(**kwargs)
        except Exception:
            logger.debug("migration_audit_failed method=%s", method, exc_info=True)

    def get_source_catalog(self) -> list[dict]:
        return list_source_catalog()

    def get_for_org(self, session_id: str, organization_id: int) -> ElfisMigrationSession:
        row = self._repo.get(session_id)
        if not row or row.organization_id != organization_id:
            raise MigrationNotFoundError("not_found", "Session introuvable")
        return row

    def get_by_session_token(
        self, organization_id: int, migration_session_token: str
    ) -> ElfisMigrationSession:
        row = self._repo.get_by_session_token(organization_id, migration_session_token)
        if not row:
            raise MigrationNotFoundError("not_found", "Session introuvable")
        return row

    def list_sessions(
        self,
        *,
        organization_id: int,
        status: str | None = None,
        mode: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ElfisMigrationSession], int]:
        return self._repo.list_sessions(
            organization_id=organization_id,
            status=status,
            mode=mode,
            limit=limit,
            offset=offset,
        )

    def create_session(
        self,
        *,
        organization_id: int,
        mode: str,
        actor_user_id: int | None,
        configuration: dict[str, Any] | None = None,
    ) -> ElfisMigrationSession:
        if mode not in {MigrationMode.INITIAL_MIGRATION.value, MigrationMode.ONE_TIME_IMPORT.value}:
            raise MigrationValidationError("mode_invalid", "Mode de migration invalide")

        if mode == MigrationMode.INITIAL_MIGRATION.value:
            existing = self._repo.find_active_initial(organization_id)
            if existing:
                raise MigrationConflictError(
                    "initial_migration_active",
                    f"Une migration initiale active existe déjà ({existing.id}). Reprenez-la.",
                )

        now = datetime.utcnow()
        token = new_session_token()
        # Garantir unicité (très rare collision)
        for _ in range(5):
            if not self._repo.token_exists(token):
                break
            token = new_session_token()

        progress = self._progress.initialize_progress(current_step=TimelineStepKey.WELCOME.value)
        row = ElfisMigrationSession(
            id=str(uuid4()),
            organization_id=organization_id,
            created_by_user_id=actor_user_id,
            migration_session_token=token,
            mode=mode,
            status=MigrationSessionStatus.DRAFT.value,
            current_step=STEP_WELCOME,
            company_profile=None,
            migration_profile=empty_profile_envelope(),
            ai_profile=empty_profile_envelope(),
            selected_sources=None,
            configuration=configuration or {},
            progress=progress,
            answers_metadata={},
            version=1,
            started_at=now,
            last_activity_at=now,
        )
        self._repo.add(row, commit=False)
        self._timeline.bootstrap_welcome(
            organization_id=organization_id,
            migration_session_id=row.id,
            commit=False,
        )
        self._activity.record_system_activity(
            organization_id=organization_id,
            migration_session_id=row.id,
            activity_type=ActivityType.MIGRATION_CREATED.value,
            severity=ActivitySeverity.SUCCESS.value,
            idempotency_key=f"created:{row.id}",
            commit=False,
        )
        self._db.commit()
        self._db.refresh(row)

        mig_metrics.incr("migration_sessions_created_total")
        logger.info(
            "migration_session_created",
            extra={
                "organization_id": organization_id,
                "migration_session_id": row.id,
                "migration_session_token": row.migration_session_token,
                "user_id": actor_user_id,
                "operation": "create_session",
                "status": "ok",
            },
        )
        self._safe_audit(
            "record_migration_session_created",
            session_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            mode=row.mode,
            old_status=None,
            new_status=row.status,
            current_step=row.current_step,
        )
        publish_migration_event(
            self._db,
            event_type="migration.session.created",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"mode": row.mode, "status": row.status},
            idempotency_key=f"migration:session:created:{organization_id}:{row.id}",
        )
        publish_migration_event(
            self._db,
            event_type="migration.step.started",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"step_key": TimelineStepKey.WELCOME.value},
            idempotency_key=f"migration:step:started:{row.id}:welcome",
        )
        publish_migration_event(
            self._db,
            event_type="migration.activity.recorded",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"activity_type": ActivityType.MIGRATION_CREATED.value},
            idempotency_key=f"migration:activity:created:{row.id}",
        )
        return row

    def _assert_modifiable(self, row: ElfisMigrationSession) -> None:
        if row.status == MigrationSessionStatus.CANCELLED.value:
            raise MigrationValidationError("session_cancelled", "Session annulée — modification interdite")
        if row.status in (
            MigrationSessionStatus.COMPLETED.value,
            MigrationSessionStatus.FAILED.value,
        ):
            raise MigrationValidationError("session_terminal", "Session terminée — modification interdite")

    def _assert_version(self, row: ElfisMigrationSession, version: int | None) -> None:
        if version is None:
            return
        if int(version) != int(row.version):
            self._activity.record_system_activity(
                organization_id=row.organization_id,
                migration_session_id=row.id,
                activity_type=ActivityType.MIGRATION_CONFLICT_DETECTED.value,
                severity=ActivitySeverity.WARNING.value,
                commit=True,
            )
            logger.info(
                "migration_version_conflict",
                extra={
                    "organization_id": row.organization_id,
                    "migration_session_id": row.id,
                    "migration_session_token": row.migration_session_token,
                    "operation": "assert_version",
                    "status": "conflict",
                },
            )
            raise MigrationConflictError(
                "version_conflict",
                "La session a été modifiée ailleurs. Rechargez puis réessayez.",
            )

    def _transition(self, row: ElfisMigrationSession, new_status: str) -> None:
        allowed = ALLOWED_TRANSITIONS.get(row.status, frozenset())
        if new_status not in allowed:
            logger.info(
                "migration_transition_error",
                extra={
                    "organization_id": row.organization_id,
                    "migration_session_id": row.id,
                    "migration_session_token": row.migration_session_token,
                    "operation": "transition",
                    "status": "error",
                    "from_status": row.status,
                    "to_status": new_status,
                },
            )
            raise MigrationValidationError(
                "transition_invalid",
                f"Transition interdite: {row.status} → {new_status}",
            )
        row.status = new_status
        row.current_step = STATUS_TO_STEP.get(new_status, row.current_step)
        row.version = int(row.version or 1) + 1

    def update_profile(
        self,
        session_id: str,
        organization_id: int,
        profile: CompanyProfileIn,
        *,
        actor_user_id: int | None,
        version: int | None = None,
    ) -> ElfisMigrationSession:
        row = self.get_for_org(session_id, organization_id)
        self._assert_modifiable(row)
        self._assert_version(row, version)

        # Token immuable — jamais écrasé
        token_before = row.migration_session_token

        old_status = row.status
        payload = profile.model_dump(mode="json")
        meta = payload.pop("answers_metadata", None) or {}
        row.company_profile = wrap_company_profile(payload)
        answers = dict(row.answers_metadata or {})
        answers.update(meta)
        row.answers_metadata = answers
        row.version = int(row.version or 1) + 1
        if row.current_step < STEP_PROFILE:
            row.current_step = STEP_PROFILE

        # Timeline : démarrer company_profile si welcome encore started
        self._timeline.complete_step(
            organization_id=organization_id,
            migration_session_id=row.id,
            step_key=TimelineStepKey.WELCOME.value,
            commit=False,
        )
        self._timeline.start_step(
            organization_id=organization_id,
            migration_session_id=row.id,
            step_key=TimelineStepKey.COMPANY_PROFILE.value,
            commit=False,
        )
        self._progress.mark_step_completed(
            row,
            TimelineStepKey.WELCOME.value,
            next_current_step=TimelineStepKey.COMPANY_PROFILE.value,
        )
        self._activity.record_user_activity(
            organization_id=organization_id,
            migration_session_id=row.id,
            activity_type=ActivityType.PROFILE_SAVED.value,
            actor_user_id=actor_user_id,
            severity=ActivitySeverity.SUCCESS.value,
            commit=False,
        )

        self._repo.save(row, commit=True)
        assert row.migration_session_token == token_before

        self._safe_audit(
            "record_migration_profile_updated",
            session_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            mode=row.mode,
            old_status=old_status,
            new_status=row.status,
            current_step=row.current_step,
        )
        publish_migration_event(
            self._db,
            event_type="migration.profile.updated",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"status": row.status},
            idempotency_key=f"migration:profile:{row.id}:{row.version}",
        )
        publish_migration_event(
            self._db,
            event_type="migration.progress.updated",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"overall_percent": (row.progress or {}).get("overall_percent")},
            idempotency_key=f"migration:progress:{row.id}:{row.version}",
        )
        return row

    def update_sources(
        self,
        session_id: str,
        organization_id: int,
        source_ids: list[str],
        *,
        actor_user_id: int | None,
        version: int | None = None,
    ) -> ElfisMigrationSession:
        row = self.get_for_org(session_id, organization_id)
        self._assert_modifiable(row)
        self._assert_version(row, version)

        cleaned = validate_selected_sources(
            source_ids,
            require_available=False,
            previously_selected=list(row.selected_sources or []),
        )
        old_status = row.status
        row.selected_sources = cleaned
        row.version = int(row.version or 1) + 1
        if row.current_step < STEP_SOURCES:
            row.current_step = STEP_SOURCES

        self._timeline.start_step(
            organization_id=organization_id,
            migration_session_id=row.id,
            step_key=TimelineStepKey.DATA_SOURCES.value,
            commit=False,
        )
        self._activity.record_user_activity(
            organization_id=organization_id,
            migration_session_id=row.id,
            activity_type=ActivityType.SOURCES_SAVED.value,
            actor_user_id=actor_user_id,
            severity=ActivitySeverity.SUCCESS.value,
            metadata={"source_count": len(cleaned)},
            commit=False,
        )

        self._repo.save(row, commit=True)
        self._safe_audit(
            "record_migration_sources_updated",
            session_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            mode=row.mode,
            old_status=old_status,
            new_status=row.status,
            current_step=row.current_step,
            source_count=len(cleaned),
        )
        publish_migration_event(
            self._db,
            event_type="migration.sources.updated",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"source_count": len(cleaned)},
            idempotency_key=f"migration:sources:{row.id}:{row.version}",
        )
        return row

    def continue_session(
        self,
        session_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None,
        version: int | None = None,
    ) -> ElfisMigrationSession:
        row = self.get_for_org(session_id, organization_id)
        self._assert_modifiable(row)
        self._assert_version(row, version)

        old_status = row.status
        if row.status == MigrationSessionStatus.DRAFT.value:
            flat = unwrap_company_profile(row.company_profile)
            if not flat:
                raise MigrationValidationError("profile_required", "Profil entreprise requis")
            CompanyProfileIn.model_validate(flat)
            self._transition(row, MigrationSessionStatus.PROFILE_COMPLETED.value)
            self._timeline.complete_step(
                organization_id=organization_id,
                migration_session_id=row.id,
                step_key=TimelineStepKey.COMPANY_PROFILE.value,
                commit=False,
            )
            self._timeline.start_step(
                organization_id=organization_id,
                migration_session_id=row.id,
                step_key=TimelineStepKey.DATA_SOURCES.value,
                commit=False,
            )
            self._progress.mark_step_completed(
                row,
                TimelineStepKey.COMPANY_PROFILE.value,
                next_current_step=TimelineStepKey.DATA_SOURCES.value,
            )
            # Ensure welcome also counted
            self._progress.mark_step_completed(
                row,
                TimelineStepKey.WELCOME.value,
                next_current_step=TimelineStepKey.DATA_SOURCES.value,
            )
        elif row.status == MigrationSessionStatus.PROFILE_COMPLETED.value:
            if not row.selected_sources:
                raise MigrationValidationError("sources_required", "Sources requises")
            validate_selected_sources(
                list(row.selected_sources),
                require_available=True,
                previously_selected=list(row.selected_sources or []),
            )
            self._transition(row, MigrationSessionStatus.SOURCES_SELECTED.value)
            self._timeline.complete_step(
                organization_id=organization_id,
                migration_session_id=row.id,
                step_key=TimelineStepKey.DATA_SOURCES.value,
                commit=False,
            )
            self._timeline.start_step(
                organization_id=organization_id,
                migration_session_id=row.id,
                step_key=TimelineStepKey.UPLOAD_PREPARATION.value,
                commit=False,
            )
            self._progress.mark_step_completed(
                row,
                TimelineStepKey.DATA_SOURCES.value,
                next_current_step=TimelineStepKey.UPLOAD_PREPARATION.value,
            )
        elif row.status == MigrationSessionStatus.SOURCES_SELECTED.value:
            validate_selected_sources(
                list(row.selected_sources or []),
                require_available=True,
                previously_selected=list(row.selected_sources or []),
            )
            self._transition(row, MigrationSessionStatus.AWAITING_UPLOAD.value)
            self._timeline.complete_step(
                organization_id=organization_id,
                migration_session_id=row.id,
                step_key=TimelineStepKey.UPLOAD_PREPARATION.value,
                commit=False,
            )
            self._timeline.ensure_entry(
                organization_id=organization_id,
                migration_session_id=row.id,
                step_key=TimelineStepKey.FILE_UPLOAD.value,
                status="pending",
                commit=False,
            )
            self._progress.mark_step_completed(
                row,
                TimelineStepKey.UPLOAD_PREPARATION.value,
                next_current_step=TimelineStepKey.FILE_UPLOAD.value,
            )
        else:
            raise MigrationValidationError(
                "continue_not_allowed",
                "Impossible de poursuivre depuis cet état",
            )

        self._activity.record_user_activity(
            organization_id=organization_id,
            migration_session_id=row.id,
            activity_type=ActivityType.STEP_COMPLETED.value,
            actor_user_id=actor_user_id,
            severity=ActivitySeverity.SUCCESS.value,
            metadata={"from_status": old_status, "to_status": row.status},
            commit=False,
        )

        self._repo.save(row, commit=True)
        self._safe_audit(
            "record_migration_step_completed",
            session_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            mode=row.mode,
            old_status=old_status,
            new_status=row.status,
            current_step=row.current_step,
        )
        publish_migration_event(
            self._db,
            event_type="migration.step.completed",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"from_status": old_status, "to_status": row.status},
            idempotency_key=f"migration:step:completed:{row.id}:{row.version}",
        )
        publish_migration_event(
            self._db,
            event_type="migration.progress.updated",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"overall_percent": (row.progress or {}).get("overall_percent")},
            idempotency_key=f"migration:progress:{row.id}:{row.version}",
        )
        return row

    def cancel_session(
        self,
        session_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None,
        reason: str | None = None,
        version: int | None = None,
    ) -> ElfisMigrationSession:
        row = self.get_for_org(session_id, organization_id)
        if row.status == MigrationSessionStatus.CANCELLED.value:
            return row
        if row.status not in CANCELABLE_STATUSES:
            raise MigrationValidationError("cancel_not_allowed", "Cette session ne peut plus être annulée")
        self._assert_version(row, version)

        old_status = row.status
        self._transition(row, MigrationSessionStatus.CANCELLED.value)
        row.cancelled_at = datetime.utcnow()
        row.cancel_reason = (reason or "").strip()[:255] or None
        self._activity.record_user_activity(
            organization_id=organization_id,
            migration_session_id=row.id,
            activity_type=ActivityType.MIGRATION_CANCELLED.value,
            actor_user_id=actor_user_id,
            severity=ActivitySeverity.WARNING.value,
            commit=False,
        )
        self._repo.save(row, commit=True)
        self._safe_audit(
            "record_migration_session_cancelled",
            session_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            mode=row.mode,
            old_status=old_status,
            new_status=row.status,
            current_step=row.current_step,
        )
        publish_migration_event(
            self._db,
            event_type="migration.session.cancelled",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"from_status": old_status},
            idempotency_key=f"migration:cancelled:{row.id}",
        )
        return row

    def resume_session(
        self,
        session_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None,
    ) -> ElfisMigrationSession:
        row = self.get_for_org(session_id, organization_id)
        if row.status == MigrationSessionStatus.CANCELLED.value:
            raise MigrationValidationError(
                "resume_cancelled",
                "Impossible de reprendre une session annulée",
            )
        if row.status == MigrationSessionStatus.COMPLETED.value:
            raise MigrationValidationError(
                "resume_completed",
                "Impossible de reprendre une session terminée",
            )
        # Ne change pas le statut — met à jour last_activity_at
        self._activity.record_user_activity(
            organization_id=organization_id,
            migration_session_id=row.id,
            activity_type=ActivityType.MIGRATION_RESUMED.value,
            actor_user_id=actor_user_id,
            severity=ActivitySeverity.INFO.value,
            # Idempotent sur double-clic : même statut + version → une seule activité
            idempotency_key=f"resume:{row.id}:{row.status}:{row.version}",
            commit=False,
        )
        self._repo.save(row, commit=True)
        mig_metrics.incr("migration_sessions_resumed_total")
        logger.info(
            "migration_session_resumed",
            extra={
                "organization_id": organization_id,
                "migration_session_id": row.id,
                "migration_session_token": row.migration_session_token,
                "user_id": actor_user_id,
                "operation": "resume_session",
                "status": "ok",
            },
        )
        publish_migration_event(
            self._db,
            event_type="migration.session.resumed",
            session=row,
            actor_user_id=actor_user_id,
            metadata={"status": row.status},
            idempotency_key=f"migration:resumed:{row.id}:{int(row.last_activity_at.timestamp()) if row.last_activity_at else 0}",
        )
        return row

    def list_timeline(self, session_id: str, organization_id: int):
        self.get_for_org(session_id, organization_id)
        return self._timeline.list_timeline(
            organization_id=organization_id,
            migration_session_id=session_id,
        )

    def list_activities(self, session_id: str, organization_id: int, *, limit: int = 50):
        self.get_for_org(session_id, organization_id)
        return self._activity.list_for_session(
            organization_id=organization_id,
            migration_session_id=session_id,
            limit=limit,
        )

    def get_progress(self, session_id: str, organization_id: int):
        row = self.get_for_org(session_id, organization_id)
        return self._progress.get_progress(row)
