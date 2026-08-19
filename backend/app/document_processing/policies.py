"""Politiques retry / timeout Document Processing."""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.config import settings

RETRYABLE_CODES = frozenset(
    {
        "timeout",
        "network_error",
        "provider_unavailable",
        "lease_lost",
        "temporary_failure",
        "noop_retryable",
    }
)

NON_RETRYABLE_CODES = frozenset(
    {
        "document_not_found",
        "version_not_found",
        "document_purged",
        "permission_denied",
        "pipeline_unknown",
        "object_quarantined",
        "invalid_transition",
        "noop_permanent",
    }
)


@dataclass(frozen=True)
class ProcessingRetryPolicy:
    max_attempts: int = 3
    initial_delay_seconds: int = 10
    max_delay_seconds: int = 300
    backoff_multiplier: float = 2.0
    jitter: bool = True

    @classmethod
    def from_settings(cls) -> ProcessingRetryPolicy:
        return cls(
            max_attempts=int(getattr(settings, "document_processing_max_attempts", 3) or 3),
            initial_delay_seconds=int(
                getattr(settings, "document_processing_retry_initial_seconds", 10) or 10
            ),
            max_delay_seconds=int(
                getattr(settings, "document_processing_retry_max_seconds", 300) or 300
            ),
        )

    def is_retryable(self, error_code: str | None) -> bool:
        code = (error_code or "").strip().lower()
        if code in NON_RETRYABLE_CODES:
            return False
        if code in RETRYABLE_CODES:
            return True
        return False

    def delay_seconds(self, attempt_number: int) -> int:
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** max(0, attempt_number - 1))
        delay = min(delay, self.max_delay_seconds)
        if self.jitter:
            delay = delay * (0.85 + random.random() * 0.3)
        return max(1, int(delay))
