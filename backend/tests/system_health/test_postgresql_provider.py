"""Tests PostgresqlHealthProvider réel (SQLite + isolation erreurs)."""

from __future__ import annotations

from app.system_health.health_thresholds import HealthThresholds
from app.system_health.health_types import HealthStatus
from app.system_health.providers.postgresql_health_provider import PostgresqlHealthProvider
from tests.system_health.conftest_helpers import make_sqlite_session_factory


def test_postgres_select_1_ok():
    factory, engine = make_sqlite_session_factory()
    provider = PostgresqlHealthProvider(
        session_factory=factory,
        engine_factory=lambda: engine,
        thresholds=HealthThresholds(postgres_latency_degraded_ms=10_000),
    )
    result = provider.check_health()
    assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    assert result.latency_ms is not None
    blob = result.model_dump_json().lower()
    for forbidden in ("password", "postgresql://", "postgres://", "database_url", "secret"):
        assert forbidden not in blob
    assert result.metadata.get("provider_mode") == "real"


def test_postgres_db_error_isolated():
    def boom():
        raise RuntimeError("connection refused simulated")

    provider = PostgresqlHealthProvider(session_factory=boom)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "db_unreachable"
    assert "Traceback" not in (result.error_message or "")


def test_postgres_latency_degraded_threshold():
    factory, engine = make_sqlite_session_factory()
    # Seuil très bas → toute latence mesurable est degraded
    provider = PostgresqlHealthProvider(
        session_factory=factory,
        engine_factory=lambda: engine,
        thresholds=HealthThresholds(
            postgres_latency_degraded_ms=0.0,
            postgres_latency_unhealthy_ms=10_000.0,
        ),
    )
    result = provider.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert result.error_code == "db_latency_high"


def test_postgres_no_secrets_even_on_url_like_error():
    def boom():
        raise RuntimeError("could not connect to postgresql://user:secret@host/db password=x")

    provider = PostgresqlHealthProvider(session_factory=boom)
    result = provider.check_health()
    msg = (result.error_message or "").lower()
    assert "postgresql://" not in msg
    assert "password" not in msg or "masqué" in msg
