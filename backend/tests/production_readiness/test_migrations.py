"""MIG — migrations / SQL (Alembic absent V1)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def test_mig_sql_scripts_present():
    required = [
        "vault_postgres.sql",
        "elfis_job_queue_postgres.sql",
        "elfis_event_bus_postgres.sql",
        "elfis_billing_postgres.sql",
        "elfis_search_engine_postgres.sql",
    ]
    for name in required:
        assert (SQL_DIR / name).is_file(), f"manquant: {name}"


def test_mig_004_delivery_index_documented():
    phase_f = Path(__file__).resolve().parents[2] / "docs" / "performance" / "postgres_indexes_phase_f.sql"
    assert phase_f.is_file()
    text = phase_f.read_text(encoding="utf-8")
    assert "uq_document_email_org_idempotency" in text


def test_mig_005_webhook_unique_in_sql_or_orm():
    billing = (SQL_DIR / "elfis_billing_postgres.sql").read_text(encoding="utf-8")
    assert "provider_event" in billing.lower() or "uq_elfis_billing" in billing.lower()


def test_mig_006_vault_hash_index():
    vault = (SQL_DIR / "vault_postgres.sql").read_text(encoding="utf-8")
    assert "checksum" in vault.lower()


def test_mig_bank2_postgres_is_additive_and_registered():
    name = "elfis_banking_bank2_postgres.sql"
    runner = Path(__file__).resolve().parents[2] / "scripts" / "rc1" / "migrate_sql.py"
    assert name in runner.read_text(encoding="utf-8")
    sql = (SQL_DIR / name).read_text(encoding="utf-8").lower()
    assert "drop" not in sql
    assert "add column if not exists account_type" in sql
    assert "add column if not exists available_balance" in sql
    assert "add column if not exists balance_updated_at" in sql
    assert "default 'other'" in sql
    assert "available_balance double precision" in sql
    assert "not null" not in sql.split("available_balance")[1].split(";")[0]
    assert "not null" not in sql.split("balance_updated_at")[1].split(";")[0]


def test_mig_bank3_postgres_is_additive_and_registered():
    name = "elfis_banking_bank3_postgres.sql"
    runner = Path(__file__).resolve().parents[2] / "scripts" / "rc1" / "migrate_sql.py"
    assert name in runner.read_text(encoding="utf-8")
    sql = (SQL_DIR / name).read_text(encoding="utf-8").lower()
    assert "drop" not in sql
    assert "add column if not exists value_date" in sql
    assert "add column if not exists counterparty_name" in sql
    assert "add column if not exists reference" in sql


def test_mig_007_search_gin():
    search = (SQL_DIR / "elfis_search_engine_postgres.sql").read_text(encoding="utf-8")
    assert "gin" in search.lower() or "tsvector" in search.lower()


@pytest.mark.skipif(
    not (os.getenv("ELFIS_PERFORMANCE_DATABASE_URL") or "").lower().startswith("postgres"),
    reason="PostgreSQL migration test NOT EXECUTED — set ELFIS_PERFORMANCE_DATABASE_URL",
)
def test_mig_001_upgrade_empty_postgres():
    """Placeholder : pas d’Alembic V1 — appliquer sql/*.sql manuellement en staging."""
    pytest.skip("Alembic non présent — migrations SQL manuelles (voir runbook)")
