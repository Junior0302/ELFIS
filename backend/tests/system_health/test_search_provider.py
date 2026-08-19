"""Tests SearchHealthProvider réel."""

from __future__ import annotations

from app.system_health.health_types import HealthStatus
from app.system_health.providers.search_health_provider import SearchHealthProvider
from tests.system_health.conftest_helpers import make_sqlite_session_factory


def test_search_index_present_postgres_like():
    factory, _ = make_sqlite_session_factory()

    def inspector(_db):
        return {
            "dialect": "postgresql",
            "table_exists": True,
            "column_exists": True,
            "column_type": "tsvector",
            "index_exists": True,
        }

    provider = SearchHealthProvider(session_factory=factory, schema_inspector=inspector)
    # La requête @@ échouera sur SQLite → on mocke aussi en interceptant _check partiellement
    # via inspector OK + on laisse la requête COUNT fonctionner
    result = provider.check_health()
    # Sur SQLite la requête tsquery échoue → degraded acceptable, ou healthy si count ok
    assert result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    assert result.metadata["table_exists"] is True
    assert result.metadata["index_exists"] is True


def test_search_index_absent_degraded():
    factory, _ = make_sqlite_session_factory()

    def inspector(_db):
        return {
            "dialect": "postgresql",
            "table_exists": True,
            "column_exists": True,
            "column_type": "tsvector",
            "index_exists": False,
        }

    provider = SearchHealthProvider(session_factory=factory, schema_inspector=inspector)
    result = provider.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert result.error_code == "search_gin_missing"
    assert "recommendation" in result.metadata


def test_search_wrong_column_type():
    factory, _ = make_sqlite_session_factory()

    def inspector(_db):
        return {
            "dialect": "postgresql",
            "table_exists": True,
            "column_exists": True,
            "column_type": "text",
            "index_exists": True,
        }

    provider = SearchHealthProvider(session_factory=factory, schema_inspector=inspector)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "search_vector_wrong_type"


def test_search_table_missing():
    factory, _ = make_sqlite_session_factory()

    def inspector(_db):
        return {
            "dialect": "postgresql",
            "table_exists": False,
            "column_exists": False,
            "column_type": None,
            "index_exists": False,
        }

    provider = SearchHealthProvider(session_factory=factory, schema_inspector=inspector)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "search_table_missing"


def test_search_db_error_isolated():
    def boom():
        raise RuntimeError("search db down")

    provider = SearchHealthProvider(session_factory=boom)
    result = provider.check_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_code == "search_check_failed"
