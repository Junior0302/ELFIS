"""Service Progress Engine — calcul côté backend uniquement."""

from __future__ import annotations

import logging
from typing import Any

from app.migration_center import metrics as mig_metrics
from app.migration_center.enums import TimelineStepKey
from app.migration_center.models import ElfisMigrationSession
from app.migration_center.progress.calculator import recalculate_from_completed
from app.migration_center.progress.schemas import MigrationProgressPayload

logger = logging.getLogger(__name__)


class MigrationProgressService:
    def initialize_progress(self, *, current_step: str = TimelineStepKey.WELCOME.value) -> dict[str, Any]:
        payload = recalculate_from_completed(
            completed_steps=[],
            current_step=current_step,
            current_step_percent=0,
        )
        return payload.to_storage()

    def get_progress(self, row: ElfisMigrationSession) -> MigrationProgressPayload:
        raw = row.progress if isinstance(row.progress, dict) else {}
        # Ignorer overall_percent venant d'un client éventuel — recalcul si structure absente
        if raw.get("schema_version") == 1 and "completed_steps" in raw:
            try:
                # Force estimated_remaining_seconds = null ; overall depuis completed
                return recalculate_from_completed(
                    completed_steps=list(raw.get("completed_steps") or []),
                    current_step=str(raw.get("current_step") or TimelineStepKey.WELCOME.value),
                    blocked_steps=list(raw.get("blocked_steps") or []),
                    warnings=list(raw.get("warnings") or []),
                    current_step_percent=int(raw.get("current_step_percent") or 0),
                )
            except Exception:
                logger.debug("migration_progress_parse_failed", exc_info=True)
        return recalculate_from_completed(
            completed_steps=[],
            current_step=TimelineStepKey.WELCOME.value,
        )

    def recalculate_progress(
        self,
        row: ElfisMigrationSession,
        *,
        completed_steps: list[str] | None = None,
        current_step: str | None = None,
        blocked_steps: list[str] | None = None,
        warnings: list[str] | None = None,
        current_step_percent: int = 0,
    ) -> dict[str, Any]:
        existing = self.get_progress(row)
        payload = recalculate_from_completed(
            completed_steps=completed_steps if completed_steps is not None else existing.completed_steps,
            current_step=current_step or existing.current_step,
            blocked_steps=blocked_steps if blocked_steps is not None else existing.blocked_steps,
            warnings=warnings if warnings is not None else existing.warnings,
            current_step_percent=current_step_percent,
        )
        stored = payload.to_storage()
        row.progress = stored
        mig_metrics.incr("migration_progress_recalculation_total")
        logger.info(
            "migration_progress_recalculated",
            extra={
                "organization_id": row.organization_id,
                "migration_session_id": row.id,
                "migration_session_token": getattr(row, "migration_session_token", None),
                "operation": "recalculate_progress",
                "status": "ok",
                "overall_percent": payload.overall_percent,
            },
        )
        return stored

    def mark_step_completed(
        self,
        row: ElfisMigrationSession,
        step_key: str,
        *,
        next_current_step: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_progress(row)
        completed = list(existing.completed_steps)
        if step_key not in completed:
            completed.append(step_key)
        return self.recalculate_progress(
            row,
            completed_steps=completed,
            current_step=next_current_step or existing.current_step,
            blocked_steps=existing.blocked_steps,
            warnings=existing.warnings,
        )

    def add_warning(self, row: ElfisMigrationSession, warning: str) -> dict[str, Any]:
        existing = self.get_progress(row)
        warnings = list(existing.warnings)
        if warning not in warnings:
            warnings.append(warning)
        return self.recalculate_progress(
            row,
            completed_steps=existing.completed_steps,
            current_step=existing.current_step,
            blocked_steps=existing.blocked_steps,
            warnings=warnings,
            current_step_percent=existing.current_step_percent,
        )

    def remove_warning(self, row: ElfisMigrationSession, warning: str) -> dict[str, Any]:
        existing = self.get_progress(row)
        warnings = [w for w in existing.warnings if w != warning]
        return self.recalculate_progress(
            row,
            completed_steps=existing.completed_steps,
            current_step=existing.current_step,
            blocked_steps=existing.blocked_steps,
            warnings=warnings,
            current_step_percent=existing.current_step_percent,
        )

    def add_blocker(self, row: ElfisMigrationSession, step_key: str) -> dict[str, Any]:
        existing = self.get_progress(row)
        blocked = list(existing.blocked_steps)
        if step_key not in blocked:
            blocked.append(step_key)
        return self.recalculate_progress(
            row,
            completed_steps=existing.completed_steps,
            current_step=existing.current_step,
            blocked_steps=blocked,
            warnings=existing.warnings,
            current_step_percent=existing.current_step_percent,
        )

    def remove_blocker(self, row: ElfisMigrationSession, step_key: str) -> dict[str, Any]:
        existing = self.get_progress(row)
        blocked = [b for b in existing.blocked_steps if b != step_key]
        return self.recalculate_progress(
            row,
            completed_steps=existing.completed_steps,
            current_step=existing.current_step,
            blocked_steps=blocked,
            warnings=existing.warnings,
            current_step_percent=existing.current_step_percent,
        )
