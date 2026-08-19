"""Tests EventsHealthProvider réel."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.system_health.health_thresholds import HealthThresholds
from app.system_health.health_types import HealthStatus
from app.system_health.providers.events_health_provider import EventsHealthProvider
from tests.system_health.conftest_helpers import make_event, make_sqlite_session_factory


def test_events_counters_healthy():
    factory, _ = make_sqlite_session_factory()
    db = factory()
    try:
        db.add(make_event(status="pending"))
        db.add(make_event(status="processed"))
        db.commit()
    finally:
        db.close()

    provider = EventsHealthProvider(
        session_factory=factory,
        thresholds=HealthThresholds(events_pending_degraded=50, events_failed_degraded=10),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.HEALTHY
    assert result.metadata["pending_count"] == 1
    assert result.metadata["backlog_count"] >= 1


def test_events_backlog_degraded():
    factory, _ = make_sqlite_session_factory()
    db = factory()
    try:
        for _ in range(4):
            db.add(make_event(status="pending"))
        db.commit()
    finally:
        db.close()

    provider = EventsHealthProvider(
        session_factory=factory,
        thresholds=HealthThresholds(events_pending_degraded=2, events_failed_degraded=100),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert result.error_code == "events_backlog"


def test_events_repo_error():
    def boom():
        raise RuntimeError("events unavailable")

    provider = EventsHealthProvider(session_factory=boom)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "events_repo_error"


def test_events_stalled_unhealthy():
    factory, _ = make_sqlite_session_factory()
    old = datetime.utcnow() - timedelta(hours=2)
    db = factory()
    try:
        db.add(make_event(status="processing", created_at=old, locked_at=old))
        db.commit()
    finally:
        db.close()

    provider = EventsHealthProvider(
        session_factory=factory,
        thresholds=HealthThresholds(events_stalled_unhealthy=1),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "events_stalled"
