"""UploadSessionService — lots de dépôt reprenables."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.audit.audit_types import AuditCategory, AuditStatus, Severity
from app.document_intake.analytics_service import UploadAnalyticsService
from app.document_intake.enums import (
    DEFAULT_MAX_ACTIVE_UPLOAD_SESSIONS,
    UPLOAD_SESSION_TRANSITIONS,
    UploadSessionStatus,
)
from app.document_intake.events import publish_upload_session_event
from app.document_intake.exceptions import (
    DocumentIntakeConflictError,
    DocumentIntakeNotFoundError,
    DocumentIntakeQuotaError,
    DocumentIntakeValidationError,
)
from app.document_intake.models import ElfisDocumentUploadSession
from app.migration_center.activity_service import MigrationActivityService

logger = logging.getLogger(__name__)

SESSION_TTL_HOURS = 72


class UploadSessionService:
    def __init__(self, db: Session, *, audit: AuditLogger | None = None) -> None:
        self._db = db
        self._audit = audit or AuditLogger(db)
        self._analytics = UploadAnalyticsService(db)
        self._activity = MigrationActivityService(db)

    def _can(self, from_status: str, to_status: str) -> bool:
        return to_status in UPLOAD_SESSION_TRANSITIONS.get(from_status, frozenset())

    def _assert_org(self, session: ElfisDocumentUploadSession, organization_id: int) -> None:
        if session.organization_id != organization_id:
            raise DocumentIntakeNotFoundError("not_found", "Session de dépôt introuvable")

    def _touch(self, session: ElfisDocumentUploadSession) -> None:
        session.last_activity_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()

    def _bump(self, session: ElfisDocumentUploadSession) -> None:
        session.version = int(session.version or 1) + 1
        self._touch(session)

    def _expire_if_needed(self, session: ElfisDocumentUploadSession) -> ElfisDocumentUploadSession:
        if session.status in (
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.COMPLETED.value,
            UploadSessionStatus.EXPIRED.value,
            UploadSessionStatus.FAILED.value,
            UploadSessionStatus.PARTIALLY_COMPLETED.value,
        ):
            return session
        if session.expires_at and session.expires_at < datetime.utcnow():
            if self._can(session.status, UploadSessionStatus.EXPIRED.value):
                session.status = UploadSessionStatus.EXPIRED.value
                self._bump(session)
                self._db.flush()
        return session

    def create_session(
        self,
        *,
        organization_id: int,
        migration_session_id: str,
        created_by_user_id: int,
        source_type: str = "manual",
        expected_file_count: int = 0,
        expected_total_bytes: int = 0,
        metadata: dict[str, Any] | None = None,
        display_label: str | None = None,
    ) -> ElfisDocumentUploadSession:
        from app.migration_center.models import ElfisMigrationSession

        mig = self._db.get(ElfisMigrationSession, migration_session_id)
        if not mig or mig.organization_id != organization_id:
            raise DocumentIntakeNotFoundError(
                "migration_session_not_found",
                "Session de migration introuvable",
            )

        active = (
            self._db.query(ElfisDocumentUploadSession)
            .filter(ElfisDocumentUploadSession.organization_id == organization_id)
            .filter(
                ElfisDocumentUploadSession.status.in_(
                    [
                        UploadSessionStatus.CREATED.value,
                        UploadSessionStatus.UPLOADING.value,
                        UploadSessionStatus.PAUSED.value,
                        UploadSessionStatus.VALIDATING.value,
                    ]
                )
            )
            .count()
        )
        if active >= DEFAULT_MAX_ACTIVE_UPLOAD_SESSIONS:
            raise DocumentIntakeQuotaError(
                "max_active_upload_sessions",
                f"Trop de sessions de dépôt actives (max {DEFAULT_MAX_ACTIVE_UPLOAD_SESSIONS})",
            )

        now = datetime.utcnow()
        seq = (
            self._db.query(ElfisDocumentUploadSession)
            .filter(ElfisDocumentUploadSession.organization_id == organization_id)
            .filter(ElfisDocumentUploadSession.migration_session_id == migration_session_id)
            .count()
        ) + 1
        row = ElfisDocumentUploadSession(
            id=str(uuid4()),
            upload_session_token=f"upl_{uuid4().hex}",
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            created_by_user_id=created_by_user_id,
            status=UploadSessionStatus.CREATED.value,
            source_type=source_type,
            display_label=display_label or f"Lot de dépôt #{seq}",
            expected_file_count=max(0, int(expected_file_count or 0)),
            expected_total_bytes=max(0, int(expected_total_bytes or 0)),
            started_at=None,
            last_activity_at=now,
            expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
            analytics_json={},
            metadata_json=dict(metadata or {}),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._analytics.initialize(row)
        self._db.add(row)
        self._db.flush()

        publish_upload_session_event(
            self._db,
            event_type="document.upload_session.created",
            session=row,
            actor_user_id=created_by_user_id,
            idempotency_key=f"document:upload_session:created:{row.id}",
            commit=False,
        )
        try:
            self._audit.service.record(
                "document_intake.upload_session.created",
                severity=Severity.INFO,
                category=AuditCategory.DOCUMENT,
                status=AuditStatus.SUCCESS,
                success=True,
                message="Session de dépôt créée",
                actor_user_id=created_by_user_id,
                organization_id=organization_id,
                service="document_intake",
                product="elfis-core",
                target_type="upload_session",
                target_id=row.id,
                metadata={"migration_session_id": migration_session_id},
            )
        except Exception:
            logger.exception("upload_session_audit_failed")

        try:
            self._activity.record_user_activity(
                migration_session_id=migration_session_id,
                organization_id=organization_id,
                actor_user_id=created_by_user_id,
                activity_type="document_upload_session_created",
                title="Session de dépôt créée",
                metadata={"upload_session_id": row.id, "label": row.display_label},
            )
        except Exception:
            logger.exception("upload_session_activity_failed")

        self._db.commit()
        self._db.refresh(row)
        return row

    def get_session(
        self, session_id: str, organization_id: int
    ) -> ElfisDocumentUploadSession:
        row = self._db.get(ElfisDocumentUploadSession, session_id)
        if not row:
            raise DocumentIntakeNotFoundError("not_found", "Session de dépôt introuvable")
        self._assert_org(row, organization_id)
        return self._expire_if_needed(row)

    def list_sessions(
        self,
        *,
        organization_id: int,
        migration_session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ElfisDocumentUploadSession], int]:
        q = self._db.query(ElfisDocumentUploadSession).filter(
            ElfisDocumentUploadSession.organization_id == organization_id
        )
        if migration_session_id:
            q = q.filter(ElfisDocumentUploadSession.migration_session_id == migration_session_id)
        total = q.count()
        rows = (
            q.order_by(ElfisDocumentUploadSession.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 200)))
            .all()
        )
        for r in rows:
            self._expire_if_needed(r)
        return rows, int(total)

    def _transition(
        self,
        session: ElfisDocumentUploadSession,
        to_status: str,
        *,
        actor_user_id: int | None,
        event_type: str,
        activity_title: str | None = None,
        activity_type: str | None = None,
        audit_action: str | None = None,
    ) -> ElfisDocumentUploadSession:
        session = self._expire_if_needed(session)
        if session.status == to_status:
            return session
        if session.status in (
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.EXPIRED.value,
        ):
            raise DocumentIntakeConflictError(
                "upload_session_closed",
                "Session de dépôt fermée",
            )
        if not self._can(session.status, to_status):
            raise DocumentIntakeConflictError(
                "invalid_upload_session_transition",
                f"Transition interdite: {session.status} -> {to_status}",
            )
        prev = session.status
        session.status = to_status
        now = datetime.utcnow()
        if to_status == UploadSessionStatus.UPLOADING.value and not session.started_at:
            session.started_at = now
        if to_status == UploadSessionStatus.CANCELLED.value:
            session.cancelled_at = now
        if to_status in (
            UploadSessionStatus.COMPLETED.value,
            UploadSessionStatus.PARTIALLY_COMPLETED.value,
        ):
            session.completed_at = now
            self._analytics.finalize(session)
        self._bump(session)
        self._db.flush()

        publish_upload_session_event(
            self._db,
            event_type=event_type,
            session=session,
            actor_user_id=actor_user_id,
            metadata={"from_status": prev, "to_status": to_status},
            idempotency_key=f"document:upload_session:{to_status}:{session.id}:{session.version}",
            commit=False,
        )
        if audit_action:
            try:
                self._audit.service.record(
                    audit_action,
                    severity=Severity.INFO,
                    category=AuditCategory.DOCUMENT,
                    status=AuditStatus.SUCCESS,
                    success=True,
                    message=activity_title or to_status,
                    actor_user_id=actor_user_id,
                    organization_id=session.organization_id,
                    service="document_intake",
                    product="elfis-core",
                    target_type="upload_session",
                    target_id=session.id,
                    metadata={"from_status": prev, "to_status": to_status},
                )
            except Exception:
                logger.exception("upload_session_audit_failed")
        if activity_title and activity_type:
            try:
                self._activity.record_user_activity(
                    migration_session_id=session.migration_session_id,
                    organization_id=session.organization_id,
                    actor_user_id=actor_user_id or session.created_by_user_id,
                    activity_type=activity_type,
                    title=activity_title,
                    metadata={"upload_session_id": session.id},
                )
            except Exception:
                logger.exception("upload_session_activity_failed")
        self._db.commit()
        self._db.refresh(session)
        return session

    def start(
        self, session_id: str, organization_id: int, *, actor_user_id: int | None = None
    ) -> ElfisDocumentUploadSession:
        s = self.get_session(session_id, organization_id)
        return self._transition(
            s,
            UploadSessionStatus.UPLOADING.value,
            actor_user_id=actor_user_id,
            event_type="document.upload_session.started",
            activity_title="Dépôt en cours",
            activity_type="document_upload_started",
        )

    def pause(
        self, session_id: str, organization_id: int, *, actor_user_id: int | None = None
    ) -> ElfisDocumentUploadSession:
        s = self.get_session(session_id, organization_id)
        return self._transition(
            s,
            UploadSessionStatus.PAUSED.value,
            actor_user_id=actor_user_id,
            event_type="document.upload_session.paused",
            activity_title="Dépôt interrompu",
            activity_type="document_upload_paused",
            audit_action="document_intake.upload_session.paused",
        )

    def resume(
        self, session_id: str, organization_id: int, *, actor_user_id: int | None = None
    ) -> ElfisDocumentUploadSession:
        s = self.get_session(session_id, organization_id)
        return self._transition(
            s,
            UploadSessionStatus.UPLOADING.value,
            actor_user_id=actor_user_id,
            event_type="document.upload_session.resumed",
            activity_title="Dépôt repris",
            activity_type="document_upload_resumed",
            audit_action="document_intake.upload_session.resumed",
        )

    def cancel(
        self, session_id: str, organization_id: int, *, actor_user_id: int | None = None
    ) -> ElfisDocumentUploadSession:
        s = self.get_session(session_id, organization_id)
        return self._transition(
            s,
            UploadSessionStatus.CANCELLED.value,
            actor_user_id=actor_user_id,
            event_type="document.upload_session.cancelled",
            activity_title="Dépôt annulé",
            activity_type="document_upload_cancelled",
            audit_action="document_intake.upload_session.cancelled",
        )

    def complete(
        self,
        session_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        partial: bool = False,
    ) -> ElfisDocumentUploadSession:
        s = self.get_session(session_id, organization_id)
        target = (
            UploadSessionStatus.PARTIALLY_COMPLETED.value
            if partial
            else UploadSessionStatus.COMPLETED.value
        )
        title = (
            "Dépôt terminé avec avertissements" if partial else "Dépôt terminé"
        )
        return self._transition(
            s,
            target,
            actor_user_id=actor_user_id,
            event_type="document.upload_session.completed",
            activity_title=title,
            activity_type="document_upload_completed",
        )

    def recalculate_counters(
        self, session: ElfisDocumentUploadSession
    ) -> ElfisDocumentUploadSession:
        self._analytics.recalculate(session)
        self._db.flush()
        return session

    def touch_activity(self, session: ElfisDocumentUploadSession) -> None:
        self._touch(session)
        self._db.flush()

    def assert_accepts_upload(
        self,
        session: ElfisDocumentUploadSession,
        *,
        organization_id: int,
        migration_session_id: str | None,
        incoming_bytes: int = 0,
    ) -> None:
        self._assert_org(session, organization_id)
        session = self._expire_if_needed(session)
        if session.status in (
            UploadSessionStatus.CANCELLED.value,
            UploadSessionStatus.EXPIRED.value,
            UploadSessionStatus.FAILED.value,
            UploadSessionStatus.COMPLETED.value,
            UploadSessionStatus.PARTIALLY_COMPLETED.value,
        ):
            raise DocumentIntakeConflictError(
                "upload_session_not_accepting",
                "Session de dépôt non disponible pour upload",
            )
        if migration_session_id and session.migration_session_id != migration_session_id:
            raise DocumentIntakeValidationError(
                "migration_mismatch",
                "La session de dépôt n'appartient pas à cette migration",
            )
        from app.document_intake.enums import (
            DEFAULT_MAX_BYTES_PER_UPLOAD_SESSION,
            DEFAULT_MAX_FILES_PER_UPLOAD_SESSION,
        )

        if session.received_file_count + 1 > DEFAULT_MAX_FILES_PER_UPLOAD_SESSION:
            raise DocumentIntakeQuotaError(
                "max_files_per_upload_session",
                f"Trop de fichiers pour ce lot (max {DEFAULT_MAX_FILES_PER_UPLOAD_SESSION})",
            )
        if session.received_total_bytes + incoming_bytes > DEFAULT_MAX_BYTES_PER_UPLOAD_SESSION:
            raise DocumentIntakeQuotaError(
                "max_bytes_per_upload_session",
                "Taille maximale du lot de dépôt dépassée",
            )
        if session.status == UploadSessionStatus.CREATED.value:
            session.status = UploadSessionStatus.UPLOADING.value
            session.started_at = session.started_at or datetime.utcnow()
            self._bump(session)
            self._db.flush()
        elif session.status == UploadSessionStatus.PAUSED.value:
            raise DocumentIntakeConflictError(
                "upload_session_paused",
                "Reprendre le dépôt avant d'envoyer des fichiers",
            )
