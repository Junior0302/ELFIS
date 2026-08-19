"""Dégradation contrôlée — isolation registry / timeout / search mock / PG partielle."""

from __future__ import annotations

from app.system_health.health_registry import HealthProviderRegistry
from app.system_health.health_thresholds import HealthThresholds
from app.system_health.health_types import HealthStatus
from app.system_health.mock_health_providers import ExplodingHealthProvider, FixedHealthProvider
from app.system_health.providers.postgresql_health_provider import PostgresqlHealthProvider
from app.system_health.providers.search_health_provider import SearchHealthProvider
from app.system_health.health_utils import run_with_timeout
from tests.system_health.conftest_helpers import make_sqlite_session_factory


def test_registry_continues_after_exception():
    reg = HealthProviderRegistry()
    reg.register(
        FixedHealthProvider(
            service_id="api",
            service_name="API",
            category="platform",
            status=HealthStatus.HEALTHY,
            summary="ok",
            latency_ms=1,
        )
    )
    reg.register(ExplodingHealthProvider())
    reg.register(
        FixedHealthProvider(
            service_id="search",
            service_name="Search",
            category="search",
            status=HealthStatus.HEALTHY,
            summary="ok",
            latency_ms=2,
        )
    )
    results = reg.check_all()
    by_id = {r.service_id: r for r in results}
    assert by_id["api"].status == HealthStatus.HEALTHY
    assert by_id["search"].status == HealthStatus.HEALTHY
    assert by_id["exploding"].status == HealthStatus.UNHEALTHY
    assert "Traceback" not in (by_id["exploding"].error_message or "")
    assert "File \"" not in (by_id["exploding"].error_message or "")


def test_provider_timeout_returns_safe_error():
    def slow():
        import time

        time.sleep(2)
        return "done"

    try:
        run_with_timeout(slow, timeout_seconds=0.1, label="timeout_test")
        assert False, "expected TimeoutError"
    except TimeoutError:
        pass


def test_postgres_partial_metrics_degraded_not_crash():
    """Session OK pour SELECT 1, engine_factory qui échoue → métriques partielles."""
    factory, _engine = make_sqlite_session_factory()

    def bad_engine():
        raise RuntimeError("pool metrics unavailable")

    provider = PostgresqlHealthProvider(
        session_factory=factory,
        engine_factory=bad_engine,
        thresholds=HealthThresholds(postgres_latency_degraded_ms=10_000),
    )
    result = provider.check_health()
    assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    assert result.status != HealthStatus.UNHEALTHY or result.error_code != "db_unreachable"
    # Sur SQLite + partial pool → degraded metrics_partial attendu
    assert result.checked_at is not None
    blob = result.model_dump_json().lower()
    assert "traceback" not in blob
    assert "postgresql://" not in blob


def test_search_index_absent_degraded_isolated():
    factory, _ = make_sqlite_session_factory()

    def inspector(_db):
        return {
            "dialect": "postgresql",
            "table_exists": True,
            "column_exists": True,
            "column_type": "tsvector",
            "index_exists": False,
        }

    reg = HealthProviderRegistry()
    reg.register(
        FixedHealthProvider(
            service_id="api",
            service_name="API",
            category="platform",
            status=HealthStatus.HEALTHY,
            summary="ok",
        )
    )
    reg.register(SearchHealthProvider(session_factory=factory, schema_inspector=inspector))
    results = reg.check_all()
    by_id = {r.service_id: r for r in results}
    assert by_id["api"].status == HealthStatus.HEALTHY
    assert by_id["search"].status == HealthStatus.DEGRADED
    assert by_id["search"].error_code == "search_gin_missing"
    assert "Traceback" not in (by_id["search"].error_message or "")
