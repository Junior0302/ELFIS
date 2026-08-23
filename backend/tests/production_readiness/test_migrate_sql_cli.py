"""CLI migrate_sql — refuse SQLite, exige DATABASE_URL."""

from __future__ import annotations

from scripts.rc1 import migrate_sql


def test_migrate_sql_main_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert migrate_sql.main() == 2


def test_migrate_sql_main_refuses_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/elfis-investor-demo.db")
    assert migrate_sql.main() == 2
