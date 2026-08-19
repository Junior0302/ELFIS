"""Cleanup — dry-run par défaut, jamais de documents métier."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.reliability.retention_service import RetentionService
from app.security.security_redaction import safe_log_context

logger = logging.getLogger("elfis.reliability.cleanup")


class CleanupService:
    def __init__(self, db: Session):
        self.db = db
        self.retention = RetentionService()

    @property
    def enabled(self) -> bool:
        return bool(getattr(settings, "elfis_cleanup_enabled", False))

    @property
    def dry_run(self) -> bool:
        return bool(getattr(settings, "elfis_cleanup_dry_run", True))

    @property
    def batch_size(self) -> int:
        return int(getattr(settings, "elfis_cleanup_batch_size", 500))

    def run(self, *, force_dry_run: bool | None = None) -> dict[str, Any]:
        dry = self.dry_run if force_dry_run is None else force_dry_run
        if not self.enabled and force_dry_run is not True:
            return {
                "status": "disabled",
                "enabled": False,
                "dry_run": dry,
                "deleted": {},
                "would_delete": {},
                "message": "Cleanup désactivé (ELFIS_CLEANUP_ENABLED=false)",
            }

        policies = self.retention.policy_map()
        summary: dict[str, Any] = {
            "status": "ok",
            "enabled": self.enabled,
            "dry_run": dry,
            "batch_size": self.batch_size,
            "would_delete": {},
            "deleted": {},
            "skipped": ["business_documents"],
        }

        # Tables opérationnelles uniquement — jamais vault documents
        targets = [
            ("security_events", "elfis_security_events", "created_at", policies.get("security_events")),
            ("job_attempts", "elfis_job_attempts", "created_at", policies.get("job_attempts")),
            ("event_attempts", "elfis_event_deliveries", "created_at", policies.get("event_attempts")),
        ]

        for key, table, col, policy in targets:
            if policy is None or policy.days <= 0:
                continue
            cutoff = datetime.utcnow() - timedelta(days=policy.days)
            count = self._count_expired(table, col, cutoff)
            summary["would_delete"][key] = count
            if dry or count == 0:
                continue
            deleted = self._delete_batch(table, col, cutoff)
            summary["deleted"][key] = deleted

        logger.info(
            "cleanup_completed",
            extra={"elfis": safe_log_context(**summary)},
        )
        return summary

    def _count_expired(self, table: str, column: str, cutoff: datetime) -> int:
        if not self._table_exists(table):
            return 0
        try:
            row = self.db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE {column} < :cutoff"),
                {"cutoff": cutoff},
            ).fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def _delete_batch(self, table: str, column: str, cutoff: datetime) -> int:
        if not self._table_exists(table):
            return 0
        try:
            # SQLite / Postgres : DELETE limité via sous-requête si possible
            result = self.db.execute(
                text(
                    f"DELETE FROM {table} WHERE id IN "
                    f"(SELECT id FROM {table} WHERE {column} < :cutoff LIMIT :lim)"
                ),
                {"cutoff": cutoff, "lim": self.batch_size},
            )
            self.db.flush()
            return int(result.rowcount or 0)
        except Exception:
            try:
                result = self.db.execute(
                    text(f"DELETE FROM {table} WHERE {column} < :cutoff"),
                    {"cutoff": cutoff},
                )
                self.db.flush()
                return min(int(result.rowcount or 0), self.batch_size)
            except Exception:
                return 0

    def _table_exists(self, table: str) -> bool:
        try:
            if settings.database_url.startswith("sqlite"):
                row = self.db.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
                    {"n": table},
                ).fetchone()
                return bool(row)
            row = self.db.execute(text("SELECT to_regclass(:n)"), {"n": table}).fetchone()
            return bool(row and row[0])
        except Exception:
            return False
