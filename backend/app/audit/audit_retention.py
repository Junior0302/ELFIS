"""Politique de rétention et archivage contrôlé des événements d'audit."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.audit_logger import AuditLogger
from app.audit.audit_models import ElfisAuditEvent, ElfisAuditEventArchive
from app.audit.audit_repository import AuditRepository
from app.audit.audit_types import AuditAction, AuditCategory, Severity
from app.config import settings

logger = logging.getLogger(__name__)


class AuditRetentionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AuditRepository(db)

    def retention_days_for(self, event: ElfisAuditEvent) -> int:
        """Durée de conservation effective — le maximum des politiques applicables."""
        days = [int(settings.audit_retention_days)]
        if (event.severity or "").upper() == Severity.CRITICAL.value:
            days.append(int(settings.audit_critical_retention_days))
        cat = (event.category or "").upper()
        if cat == AuditCategory.SECURITY.value:
            days.append(int(settings.audit_security_retention_days))
        if cat == AuditCategory.AUTH.value:
            days.append(int(settings.audit_auth_retention_days))
        return max(days)

    def calculate_expiration(self, event: ElfisAuditEvent) -> datetime:
        base = event.occurred_at or datetime.utcnow()
        return base + timedelta(days=self.retention_days_for(event))

    def is_expired(self, event: ElfisAuditEvent, *, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        return self.calculate_expiration(event) <= now

    def preview_retention(
        self,
        *,
        now: datetime | None = None,
        sample_limit: int = 5000,
        before: datetime | None = None,
    ) -> dict[str, Any]:
        """Aperçu sans modification — candidats expirés selon politique."""
        now = now or datetime.utcnow()
        # Fenêtre large : événements plus vieux que la rétention minimale
        min_days = min(
            int(settings.audit_retention_days),
            int(settings.audit_auth_retention_days),
            int(settings.audit_security_retention_days),
            int(settings.audit_critical_retention_days),
        )
        cutoff = before or (now - timedelta(days=min_days))
        candidates = self._repo.list_candidates_before(before=cutoff, limit=sample_limit)
        expired: list[dict[str, Any]] = []
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for ev in candidates:
            if not self.is_expired(ev, now=now):
                continue
            expired.append(
                {
                    "id": ev.id,
                    "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                    "category": ev.category,
                    "severity": ev.severity,
                    "action": ev.action,
                    "expires_at": self.calculate_expiration(ev).isoformat(),
                    "retention_days": self.retention_days_for(ev),
                }
            )
            by_category[ev.category or "OTHER"] = by_category.get(ev.category or "OTHER", 0) + 1
            by_severity[ev.severity or "INFO"] = by_severity.get(ev.severity or "INFO", 0) + 1

        return {
            "now": now.isoformat(),
            "sample_scanned": len(candidates),
            "expired_count": len(expired),
            "by_category": by_category,
            "by_severity": by_severity,
            "sample": expired[:50],
            "policy": {
                "default_days": settings.audit_retention_days,
                "security_days": settings.audit_security_retention_days,
                "auth_days": settings.audit_auth_retention_days,
                "critical_days": settings.audit_critical_retention_days,
            },
            "note": "Preview uniquement — aucune écriture",
        }

    def list_expired_candidates(
        self,
        *,
        now: datetime | None = None,
        batch_size: int | None = None,
        before: datetime | None = None,
    ) -> list[ElfisAuditEvent]:
        now = now or datetime.utcnow()
        batch = batch_size or int(settings.audit_archive_batch_size)
        min_days = min(
            int(settings.audit_retention_days),
            int(settings.audit_auth_retention_days),
        )
        cutoff = before or (now - timedelta(days=min_days))
        raw = self._repo.list_candidates_before(before=cutoff, limit=max(batch * 5, batch))
        out: list[ElfisAuditEvent] = []
        for ev in raw:
            if self.is_expired(ev, now=now):
                out.append(ev)
            if len(out) >= batch:
                break
        return out

    def archive_expired(
        self,
        *,
        confirm: bool = False,
        batch_size: int | None = None,
        before: datetime | None = None,
        actor_user_id: int | None = None,
        reason: str = "retention_policy",
    ) -> dict[str, Any]:
        if not confirm:
            raise ValueError("confirmation_required")
        now = datetime.utcnow()
        batch_id = str(uuid4())
        candidates = self.list_expired_candidates(
            now=now, batch_size=batch_size, before=before
        )
        archived = 0
        skipped = 0
        errors = 0
        for ev in candidates:
            try:
                with self._db.begin_nested():
                    if self._repo.archive_exists(ev.id):
                        self._repo.delete_live(ev.id)
                        skipped += 1
                    else:
                        arch = ElfisAuditEventArchive(
                            id=ev.id,
                            occurred_at=ev.occurred_at,
                            severity=ev.severity,
                            category=ev.category,
                            action=ev.action,
                            status=ev.status,
                            actor_user_id=ev.actor_user_id,
                            actor_email=ev.actor_email,
                            organization_id=ev.organization_id,
                            product=ev.product,
                            service=ev.service,
                            target_type=ev.target_type,
                            target_id=ev.target_id,
                            target_display=ev.target_display,
                            request_id=ev.request_id,
                            correlation_id=ev.correlation_id,
                            ip_address=ev.ip_address,
                            user_agent=ev.user_agent,
                            metadata_json=ev.metadata_json,
                            message=ev.message,
                            duration_ms=ev.duration_ms,
                            success=ev.success,
                            archived_at=now,
                            archive_batch_id=batch_id,
                            archive_reason=reason[:128],
                        )
                        self._repo.insert_archive(arch, flush=True)
                        self._repo.delete_live(ev.id)
                        archived += 1
            except Exception:  # noqa: BLE001
                errors += 1
                logger.warning("audit_archive_row_failed", extra={"event_id": ev.id}, exc_info=True)
                continue
        try:
            self._db.commit()
        except Exception:  # noqa: BLE001
            self._db.rollback()
            raise

        result = {
            "batch_id": batch_id,
            "candidates": len(candidates),
            "archived": archived,
            "already_archived_removed": skipped,
            "errors": errors,
            "archive_total": self._repo.count_archive(),
        }
        try:
            AuditLogger(isolated_writes=True).service.record(
                AuditAction.AUDIT_ARCHIVE_COMPLETED.value,
                category=AuditCategory.SECURITY,
                severity=Severity.INFO,
                success=errors == 0,
                actor_user_id=actor_user_id,
                service="audit_retention",
                message="Archivage rétention audit",
                metadata={
                    "batch_id": batch_id,
                    "archived": archived,
                    "errors": errors,
                    "candidates": len(candidates),
                },
            )
        except Exception:  # noqa: BLE001
            logger.warning("audit_archive_meta_failed", exc_info=True)
        return result

    def purge_archived_according_to_policy(
        self,
        *,
        confirm: bool = False,
        extra_days: int | None = None,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        """Purge optionnelle des archives très anciennes (jamais silencieuse)."""
        if not confirm:
            raise ValueError("confirmation_required")
        keep_days = int(extra_days if extra_days is not None else settings.audit_critical_retention_days)
        before = datetime.utcnow() - timedelta(days=keep_days)
        batch = batch_size or int(settings.audit_archive_batch_size)
        deleted = self._repo.purge_archive_before(before=before, limit=batch)
        self._db.commit()
        return {
            "deleted": deleted,
            "before": before.isoformat(),
            "keep_days": keep_days,
            "note": "Purge archive uniquement — événements live non touchés",
        }
