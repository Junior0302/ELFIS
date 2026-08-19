"""Conftest concurrence PostgreSQL — isolé du conftest fonctionnel SQLite."""

from __future__ import annotations

import pytest

from tests.concurrency.postgres_helpers import ensure_postgres_test_env


@pytest.fixture(scope="session", autouse=True)
def _rc258_postgres_env():
    ensure_postgres_test_env()
    yield
