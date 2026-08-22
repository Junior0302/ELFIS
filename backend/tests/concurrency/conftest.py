"""Conftest concurrence — PostgreSQL RC1 + SQLite NullPool pour charge parallèle."""

from __future__ import annotations

import pytest

from tests.concurrency.postgres_helpers import ensure_postgres_test_env
from tests.concurrency.sqlite_recette import build_concurrency_sqlite_recette


@pytest.fixture(scope="session", autouse=True)
def _rc258_postgres_env():
    ensure_postgres_test_env()
    yield


@pytest.fixture()
def concurrency_db(tmp_path, monkeypatch):
    """SQLite recette avec NullPool : une connexion DB par Session/request thread."""
    yield from build_concurrency_sqlite_recette(tmp_path, monkeypatch)
