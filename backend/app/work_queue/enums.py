"""Work Queue V1 — organisation opérationnelle des décisions."""

from __future__ import annotations

from enum import StrEnum


class WorkQueueBucket(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    COMPLETED = "completed"


class WaitingReasonCode(StrEnum):
    ANALYSIS_IN_PROGRESS = "analysis_in_progress"
    EXECUTION_RUNNING = "execution_running"
    EXECUTION_PENDING = "execution_pending"
    SOURCE_UPDATING = "source_updating"
    ACTION_TEMPORARILY_UNAVAILABLE = "action_temporarily_unavailable"


COMPLETED_LOOKBACK_DAYS = 30
MAX_SEARCH_LENGTH = 80
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50
