"""Provider réel — Event Bus (lecture seule, agrégats SQL)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.events.event_models import ElfisEvent
from app.events.event_schemas import EventStatus
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_thresholds import HealthThresholds, load_thresholds
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)

_PENDING_STATUSES = (EventStatus.pending.value, EventStatus.retry.value)
_FAILED_STATUSES = (EventStatus.failed.value, EventStatus.dead_letter.value)


def _default_session_factory() -> Session:
    from app.database import SessionLocal

    return SessionLocal()


class EventsHealthProvider(HealthProvider):
    service_id = "event_bus"
    service_name = "Event Bus"
    category = HealthCategory.WORKERS.value

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        thresholds: HealthThresholds | None = None,
        timeout_seconds: float | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory or _default_session_factory
        self._thresholds = thresholds or load_thresholds()
        self._timeout = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else self._thresholds.provider_timeout_seconds
        )
        self._now_fn = now_fn or utcnow

    def check_health(self) -> HealthCheckResult:
        try:
            return run_with_timeout(self._check, timeout_seconds=self._timeout, label=self.service_id)
        except Exception as exc:
            logger.warning("system_health_events_failed", extra={"error": type(exc).__name__})
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Bus d'événements inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="events_repo_error",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        db = self._session_factory()
        now = self._now_fn()
        try:
            t0 = time.perf_counter()
            rows = (
                db.query(ElfisEvent.status, func.count(ElfisEvent.id)).group_by(ElfisEvent.status).all()
            )
            counts = {str(s): int(c) for s, c in rows}

            pending = sum(counts.get(s, 0) for s in _PENDING_STATUSES)
            processing = counts.get(EventStatus.processing.value, 0)
            failed = sum(counts.get(s, 0) for s in _FAILED_STATUSES)
            backlog = pending + processing

            oldest_created = (
                db.query(func.min(ElfisEvent.created_at))
                .filter(ElfisEvent.status.in_(_PENDING_STATUSES))
                .scalar()
            )
            oldest_pending_age_seconds: int | None = None
            if oldest_created is not None:
                oldest_pending_age_seconds = max(0, int((now - oldest_created).total_seconds()))

            lock_timeout = int(getattr(settings, "elfis_event_lock_timeout_seconds", 300) or 300)
            lock_cutoff = now - timedelta(seconds=lock_timeout)
            stalled = (
                db.query(func.count(ElfisEvent.id))
                .filter(
                    ElfisEvent.status == EventStatus.processing.value,
                    ElfisEvent.locked_at.isnot(None),
                    ElfisEvent.locked_at < lock_cutoff,
                )
                .scalar()
            )
            stalled_count = int(stalled or 0)

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            thr = self._thresholds

            status = HealthStatus.HEALTHY
            summary = "Bus opérationnel — claim nominal"
            error_code = None
            error_message = None

            if stalled_count >= thr.events_stalled_unhealthy:
                status = HealthStatus.UNHEALTHY
                summary = f"{stalled_count} événement(s) bloqué(s)"
                error_code = "events_stalled"
                error_message = "Events processing avec verrou expiré"
            elif pending >= thr.events_pending_degraded:
                status = HealthStatus.DEGRADED
                summary = f"Backlog events — {pending} pending"
                error_code = "events_backlog"
            elif failed >= thr.events_failed_degraded:
                status = HealthStatus.DEGRADED
                summary = f"{failed} événement(s) en échec"
                error_code = "events_failed"
            elif (
                oldest_pending_age_seconds is not None
                and oldest_pending_age_seconds >= thr.events_oldest_pending_degraded_seconds
            ):
                status = HealthStatus.DEGRADED
                summary = f"Plus vieux pending trop ancien ({oldest_pending_age_seconds}s)"
                error_code = "events_oldest_pending"

            metrics = [
                metric("pending", "Events pending", pending, unit="events", status=status.value),
                metric("processing", "Events processing", processing, unit="events"),
                metric("failed", "Events failed", failed, unit="events"),
                metric("backlog_count", "Backlog", backlog, unit="events"),
                metric(
                    "oldest_pending_age_seconds",
                    "Âge plus vieux pending",
                    oldest_pending_age_seconds,
                    unit="s",
                ),
                metric("stalled_count", "Events bloqués", stalled_count, unit="events"),
                metric(
                    "pending_events",
                    "Events pending",
                    pending,
                    unit="events",
                    description="Alias compatibilité métriques mock",
                ),
            ]

            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=status,
                summary=summary,
                latency_ms=latency_ms,
                checked_at=utcnow(),
                version="v1",
                metrics=metrics,
                metadata={
                    "provider_mode": "real",
                    "simulated": False,
                    "pending_count": pending,
                    "processing_count": processing,
                    "failed_count": failed,
                    "backlog_count": backlog,
                    "oldest_pending_age_seconds": oldest_pending_age_seconds,
                    "stalled_count": stalled_count,
                },
                error_code=error_code,
                error_message=error_message,
            )
        finally:
            db.close()
