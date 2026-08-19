"""Calcul de progression basé sur les étapes complétées."""

from __future__ import annotations

from datetime import datetime

from app.migration_center.enums import ALL_TIMELINE_STEPS
from app.migration_center.progress.constants import PROGRESS_WEIGHTS
from app.migration_center.progress.schemas import MigrationProgressPayload


def recalculate_from_completed(
    *,
    completed_steps: list[str],
    current_step: str,
    blocked_steps: list[str] | None = None,
    warnings: list[str] | None = None,
    current_step_percent: int = 0,
) -> MigrationProgressPayload:
    completed = []
    seen: set[str] = set()
    for s in completed_steps:
        if s in PROGRESS_WEIGHTS and s not in seen:
            completed.append(s)
            seen.add(s)

    overall = sum(PROGRESS_WEIGHTS[s] for s in completed)
    overall = max(0, min(100, int(overall)))

    blocked = [b for b in (blocked_steps or []) if b in PROGRESS_WEIGHTS]
    pending = [s for s in ALL_TIMELINE_STEPS if s not in seen and s not in blocked]

    cur = current_step if current_step in PROGRESS_WEIGHTS else "welcome"
    return MigrationProgressPayload(
        schema_version=1,
        overall_percent=overall,
        current_step=cur,
        current_step_percent=max(0, min(100, int(current_step_percent))),
        completed_steps=completed,
        pending_steps=pending,
        blocked_steps=blocked,
        warnings=list(warnings or []),
        estimated_remaining_seconds=None,
        updated_at=datetime.utcnow(),
    )
