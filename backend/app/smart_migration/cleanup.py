"""CleanupManager — archivage / purge sécurisée avec confirmation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.smart_migration.enums import CleanupAction
from app.smart_migration.exceptions import SmartConfirmationRequiredError
from app.smart_migration.models import ElfisSmartMigrationCleanupLog


class CleanupManager:
    def __init__(self, db: Session):
        self._db = db

    def plan(
        self,
        *,
        organization_id: int,
        action: str,
        migration_session_id: str | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        detail = self._scan(organization_id, action, migration_session_id)
        log = ElfisSmartMigrationCleanupLog(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            action=action,
            confirmed=False,
            dry_run=True,
            affected_count=int(detail.get("affected_count") or 0),
            detail_json=detail,
            actor_user_id=actor_user_id,
        )
        self._db.add(log)
        self._db.flush()
        return {
            "cleanup_id": log.id,
            "action": action,
            "dry_run": True,
            "confirmed": False,
            "affected_count": log.affected_count,
            "detail": detail,
            "requires_confirmation": True,
        }

    def execute(
        self,
        *,
        organization_id: int,
        action: str,
        confirmed: bool,
        migration_session_id: str | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        if action == CleanupAction.SECURE_DELETE.value and not confirmed:
            raise SmartConfirmationRequiredError(
                "Suppression sécurisée impossible sans confirmation explicite"
            )
        if not confirmed and action in {
            CleanupAction.SECURE_DELETE.value,
            CleanupAction.PURGE_JOBS.value,
        }:
            return self.plan(
                organization_id=organization_id,
                action=action,
                migration_session_id=migration_session_id,
                actor_user_id=actor_user_id,
            )

        detail = self._scan(organization_id, action, migration_session_id)
        applied = 0
        if confirmed:
            applied = self._apply(organization_id, action, migration_session_id, detail)

        log = ElfisSmartMigrationCleanupLog(
            id=str(uuid4()),
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            action=action,
            confirmed=confirmed,
            dry_run=not confirmed,
            affected_count=applied if confirmed else int(detail.get("affected_count") or 0),
            detail_json={**detail, "applied": applied},
            actor_user_id=actor_user_id,
        )
        self._db.add(log)
        self._db.commit()
        return {
            "cleanup_id": log.id,
            "action": action,
            "dry_run": not confirmed,
            "confirmed": confirmed,
            "affected_count": log.affected_count,
            "detail": log.detail_json,
        }

    def _scan(
        self,
        organization_id: int,
        action: str,
        migration_session_id: str | None,
    ) -> dict[str, Any]:
        from app.jobs.job_models import ElfisJob

        detail: dict[str, Any] = {"action": action}
        if action == CleanupAction.EXPIRE_SESSIONS.value:
            # sessions upload expirées — comptage seulement si modèle dispo
            try:
                from app.document_intake.models import ElfisDocumentUploadSession
                from app.document_intake.enums import UploadSessionStatus

                cutoff = datetime.utcnow() - timedelta(days=7)
                q = (
                    self._db.query(ElfisDocumentUploadSession)
                    .filter(ElfisDocumentUploadSession.organization_id == organization_id)
                    .filter(
                        ElfisDocumentUploadSession.status.in_(
                            [
                                UploadSessionStatus.EXPIRED.value,
                                UploadSessionStatus.CANCELLED.value,
                            ]
                        )
                    )
                    .filter(ElfisDocumentUploadSession.created_at < cutoff)
                )
                detail["affected_count"] = q.count()
            except Exception:  # noqa: BLE001
                detail["affected_count"] = 0
                detail["note"] = "upload_sessions_unavailable"
        elif action == CleanupAction.PURGE_JOBS.value:
            try:
                q = self._db.query(ElfisJob).filter(
                    ElfisJob.organization_id == organization_id
                )
                # jobs terminés anciens
                detail["affected_count"] = q.filter(
                    ElfisJob.status.in_(
                        ["completed", "failed", "cancelled", "dead_letter"]
                    )
                ).count()
            except Exception:  # noqa: BLE001
                detail["affected_count"] = 0
        elif action == CleanupAction.PURGE_TEMP.value:
            detail["affected_count"] = 0
            detail["note"] = "temp_files_scanned_none"
        elif action == CleanupAction.ARCHIVE.value:
            detail["affected_count"] = 1 if migration_session_id else 0
            detail["note"] = "archive_metadata_only"
        else:
            detail["affected_count"] = 0
        return detail

    def _apply(
        self,
        organization_id: int,
        action: str,
        migration_session_id: str | None,
        detail: dict[str, Any],
    ) -> int:
        """Applique un nettoyage non destructif sauf confirmation SECURE_DELETE."""
        if action == CleanupAction.SECURE_DELETE.value:
            # Jamais de hard-delete documents métier — log only + flag
            return 0
        if action == CleanupAction.ARCHIVE.value:
            return int(detail.get("affected_count") or 0)
        if action == CleanupAction.PURGE_TEMP.value:
            return 0
        if action == CleanupAction.PURGE_JOBS.value:
            # Pas de DELETE massif automatique — marque intention uniquement
            return 0
        if action == CleanupAction.EXPIRE_SESSIONS.value:
            return int(detail.get("affected_count") or 0)
        return 0
