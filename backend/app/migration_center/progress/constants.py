"""Pondérations étapes — somme = 100."""

from __future__ import annotations

from app.migration_center.enums import TimelineStepKey

PROGRESS_WEIGHTS: dict[str, int] = {
    TimelineStepKey.WELCOME.value: 5,
    TimelineStepKey.COMPANY_PROFILE.value: 15,
    TimelineStepKey.DATA_SOURCES.value: 15,
    TimelineStepKey.UPLOAD_PREPARATION.value: 5,
    TimelineStepKey.FILE_UPLOAD.value: 15,
    TimelineStepKey.ANALYSIS.value: 20,
    TimelineStepKey.VALIDATION.value: 15,
    TimelineStepKey.IMPORT.value: 8,
    TimelineStepKey.COMPLETION.value: 2,
}

TOTAL_WEIGHT = sum(PROGRESS_WEIGHTS.values())
assert TOTAL_WEIGHT == 100, f"PROGRESS_WEIGHTS must sum to 100, got {TOTAL_WEIGHT}"

PROGRESS_SCHEMA_VERSION = 1
