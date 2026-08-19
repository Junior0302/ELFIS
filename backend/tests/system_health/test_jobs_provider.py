"""Tests JobsHealthProvider réel."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.jobs.job_types import JobStatus
from app.system_health.health_thresholds import HealthThresholds
from app.system_health.health_types import HealthStatus
from app.system_health.providers.jobs_health_provider import JobsHealthProvider
from tests.system_health.conftest_helpers import make_job, make_sqlite_session_factory


def test_jobs_counters_healthy():
    factory, _ = make_sqlite_session_factory()
    db = factory()
    try:
        db.add(make_job(status=JobStatus.PENDING))
        db.add(make_job(status=JobStatus.COMPLETED, completed_at=datetime.utcnow()))
        db.commit()
    finally:
        db.close()

    provider = JobsHealthProvider(
        session_factory=factory,
        thresholds=HealthThresholds(jobs_pending_degraded=50, jobs_failed_degraded=10),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.HEALTHY
    keys = {m.key: m.value for m in result.metrics}
    assert keys["pending"] == 1
    assert keys["completed_recent_count"] >= 1
    assert result.metadata["pending_count"] == 1


def test_jobs_backlog_degraded():
    factory, _ = make_sqlite_session_factory()
    db = factory()
    try:
        for _ in range(5):
            db.add(make_job(status=JobStatus.PENDING))
        db.commit()
    finally:
        db.close()

    provider = JobsHealthProvider(
        session_factory=factory,
        thresholds=HealthThresholds(jobs_pending_degraded=3, jobs_failed_degraded=100),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert result.error_code == "jobs_backlog"


def test_jobs_repo_error():
    def boom():
        raise RuntimeError("db down")

    provider = JobsHealthProvider(session_factory=boom)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "jobs_repo_error"


def test_jobs_stalled_unhealthy():
    factory, _ = make_sqlite_session_factory()
    old = datetime.utcnow() - timedelta(hours=2)
    db = factory()
    try:
        db.add(
            make_job(
                status=JobStatus.PROCESSING,
                created_at=old,
                locked_at=old,
                heartbeat_at=old,
            )
        )
        db.commit()
    finally:
        db.close()

    provider = JobsHealthProvider(
        session_factory=factory,
        thresholds=HealthThresholds(jobs_stalled_unhealthy=1),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "jobs_stalled"
