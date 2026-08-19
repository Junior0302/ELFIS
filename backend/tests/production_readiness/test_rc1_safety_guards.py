"""Tests unitaires des garde-fous RC1 (sans PostgreSQL)."""

from __future__ import annotations

import pytest

from scripts.rc1.safety import (
    assert_safe_postgres_url,
    assert_safe_rc1_environment,
    mask_database_url,
)


def test_mask_database_url_hides_password():
    masked = mask_database_url("postgresql+psycopg://elfis:SuperSecret@localhost:5432/elfis_rc1_recette")
    assert "SuperSecret" not in masked
    assert "***" in masked
    assert "elfis_rc1_recette" in masked


def test_refuse_production_database_name():
    with pytest.raises(RuntimeError):
        assert_safe_postgres_url("postgresql://u:p@localhost/elfis_production")


def test_refuse_sqlite():
    with pytest.raises(RuntimeError):
        assert_safe_postgres_url("sqlite:///./x.db")


def test_refuse_without_recette_marker():
    with pytest.raises(RuntimeError):
        assert_safe_postgres_url("postgresql://u:p@localhost/elfis_core")


def test_accept_recette_name():
    url = assert_safe_postgres_url("postgresql+psycopg://u:p@localhost/elfis_rc1_recette")
    assert "rc1" in url or "recette" in url


def test_reset_requires_flag(monkeypatch):
    monkeypatch.delenv("ELFIS_ALLOW_DATABASE_RESET", raising=False)
    with pytest.raises(RuntimeError):
        assert_safe_postgres_url(
            "postgresql://u:p@localhost/elfis_rc1_test",
            allow_reset=True,
        )


def test_environment_rejects_production(monkeypatch):
    monkeypatch.setenv("ELFIS_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError):
        assert_safe_rc1_environment()
