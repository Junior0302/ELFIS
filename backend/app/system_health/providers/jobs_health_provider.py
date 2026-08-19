"""Provider réel — Jobs Queue (lecture seule, agrégats SQL)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobStatus
from app.system_health.health_provider import HealthProvider
from app.system_health.health_schemas import HealthCheckResult
from app.system_health.health_thresholds import HealthThresholds, load_thresholds
from app.system_health.health_types import HealthCategory, HealthStatus
from app.system_health.health_utils import metric, run_with_timeout, safe_error_message, utcnow

logger = logging.getLogger(__name__)

_PENDING_STATUSES = (JobStatus.PENDING, JobStatus.SCHEDULED, JobStatus.RETRY)
_FAILED_STATUSES = (JobStatus.FAILED, JobStatus.DEAD_LETTER)


def _default_session_factory() -> Session:
    from app.database import SessionLocal

    return SessionLocal()


class JobsHealthProvider(HealthProvider):
    service_id = "jobs_queue"
    service_name = "Jobs Queue"
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
            logger.warning("system_health_jobs_failed", extra={"error": type(exc).__name__})
            return HealthCheckResult(
                service_id=self.service_id,
                service_name=self.service_name,
                category=self.category,
                status=HealthStatus.UNHEALTHY,
                summary="Queue jobs inaccessible",
                latency_ms=None,
                checked_at=utcnow(),
                version="v1",
                metrics=[],
                metadata={"provider_mode": "real", "simulated": False},
                error_code="jobs_repo_error",
                error_message=safe_error_message(exc),
            )

    def _check(self) -> HealthCheckResult:
        db = self._session_factory()
        now = self._now_fn()
        try:
            t0 = time.perf_counter()
            rows = db.query(ElfisJob.status, func.count(ElfisJob.id)).group_by(ElfisJob.status).all()
            counts = {str(s): int(c) for s, c in rows}

            pending = sum(counts.get(s, 0) for s in _PENDING_STATUSES)
            running = counts.get(JobStatus.PROCESSING, 0)
            failed = sum(counts.get(s, 0) for s in _FAILED_STATUSES)
            completed = counts.get(JobStatus.COMPLETED, 0)

            recent_cutoff = now - timedelta(hours=24)
            completed_recent = (
                db.query(func.count(ElfisJob.id))
                .filter(
                    ElfisJob.status == JobStatus.COMPLETED,
                    ElfisJob.completed_at.isnot(None),
                    ElfisJob.completed_at >= recent_cutoff,
                )
                .scalar()
            )
            completed_recent_count = int(completed_recent or 0)

            oldest_created = (
                db.query(func.min(ElfisJob.created_at))
                .filter(ElfisJob.status.in_(_PENDING_STATUSES))
                .scalar()
            )
            oldest_pending_age_seconds: int | None = None
            if oldest_created is not None:
                oldest_pending_age_seconds = max(0, int((now - oldest_created).total_seconds()))

            lock_timeout = int(getattr(settings, "elfis_job_lock_timeout_seconds", 300) or 300)
            lock_cutoff = now - timedelta(seconds=lock_timeout)
            stalled = (
                db.query(func.count(ElfisJob.id))
                .filter(
                    ElfisJob.status == JobStatus.PROCESSING,
                    or_(
                        and_(
                            ElfisJob.heartbeat_at.isnot(None),
                            ElfisJob.heartbeat_at < lock_cutoff,
                        ),
                        and_(
                            ElfisJob.heartbeat_at.is_(None),
                            ElfisJob.locked_at.isnot(None),
                            ElfisJob.locked_at < lock_cutoff,
                        ),
                    ),
                )
                .scalar()
            )
            stalled_count = int(stalled or 0)

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            thr = self._thresholds

            status = HealthStatus.HEALTHY
            summary = "File jobs nominale"
            error_code = None
            error_message = None

            if stalled_count >= thr.jobs_stalled_unhealthy:
                status = HealthStatus.UNHEALTHY
                summary = f"{stalled_count} job(s) bloqué(s)"
                error_code = "jobs_stalled"
                error_message = "Jobs processing sans heartbeat dans le timeout de verrou"
            elif pending >= thr.jobs_pending_degraded:
                status = HealthStatus.DEGRADED
                summary = f"Backlog jobs — {pending} pending"
                error_code = "jobs_backlog"
            elif failed >= thr.jobs_failed_degraded:
                status = HealthStatus.DEGRADED
                summary = f"{failed} job(s) en échec"
                error_code = "jobs_failed"
            elif (
                oldest_pending_age_seconds is not None
                and oldest_pending_age_seconds >= thr.jobs_oldest_pending_degraded_seconds
            ):
                status = HealthStatus.DEGRADED
                summary = f"Plus vieux pending trop ancien ({oldest_pending_age_seconds}s)"
                error_code = "jobs_oldest_pending"

            metrics = [
                metric("pending", "Jobs pending", pending, unit="jobs", status=status.value),
                metric("running", "Jobs running", running, unit="jobs"),
                metric("failed", "Jobs failed", failed, unit="jobs"),
                metric(
                    "completed_recent_count",
                    "Complétés (24h)",
                    completed_recent_count,
                    unit="jobs",
                ),
                metric(
                    "oldest_pending_age_seconds",
                    "Âge plus vieux pending",
                    oldest_pending_age_seconds,
                    unit="s",
                ),
                metric("stalled_count", "Jobs bloqués", stalled_count, unit="jobs"),
                metric("completed_total", "Complétés (total)", completed, unit="jobs"),
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
                    "running_count": running,
                    "failed_count": failed,
                    "completed_recent_count": completed_recent_count,
                    "oldest_pending_age_seconds": oldest_pending_age_seconds,
                    "stalled_count": stalled_count,
                },
                error_code=error_code,
                error_message=error_message,
            )
        finally:
            db.close()
