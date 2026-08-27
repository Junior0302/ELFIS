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


def test_mig_bank31_postgres_is_additive_and_registered():
    name = "elfis_banking_bank31_postgres.sql"
    runner = Path(__file__).resolve().parents[2] / "scripts" / "rc1" / "migrate_sql.py"
    runner_text = runner.read_text(encoding="utf-8")
    assert name in runner_text
    assert runner_text.index("elfis_banking_bank3_postgres.sql") < runner_text.index(name)
    sql = (SQL_DIR / name).read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "drop table" not in lowered
    assert "delete from" not in lowered
    assert "uq_bank_transactions_account_external_id" in sql
    assert "ck_bank_transactions_external_id_trimmed" in sql
    assert "account_id" in sql
    assert "external_id" in sql
    assert "CREATE UNIQUE INDEX" in sql
    assert "btrim(external_id)" in sql
    ddl = sql.split("CREATE UNIQUE INDEX", 1)[1].lower()
    assert "fingerprint" not in ddl
    assert "update " not in lowered
    checker = Path(__file__).resolve().parents[2] / "scripts" / "production" / "check_migrations.py"
    assert name in checker.read_text(encoding="utf-8")


def test_mig_bank4_postgres_is_additive_and_registered():
    name = "elfis_banking_bank4_postgres.sql"
    runner = Path(__file__).resolve().parents[2] / "scripts" / "rc1" / "migrate_sql.py"
    runner_text = runner.read_text(encoding="utf-8")
    assert name in runner_text
    assert runner_text.index("elfis_banking_bank31_postgres.sql") < runner_text.index(name)
    sql = (SQL_DIR / name).read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "drop table" not in lowered
    assert "delete from" not in lowered
    assert "last_sync_started_at" in sql
    assert "last_sync_status" in sql
    assert "consecutive_sync_failures" in sql
    assert "elfis_bank_webhook_receipts" in sql
    assert "uq_elfis_bank_webhook_provider_event" in sql
    assert "client_secret" not in lowered
    assert "iban" not in lowered
    checker = Path(__file__).resolve().parents[2] / "scripts" / "production" / "check_migrations.py"
    assert name in checker.read_text(encoding="utf-8")


def test_mig_007_search_gin():
    search = (SQL_DIR / "elfis_search_engine_postgres.sql").read_text(encoding="utf-8")
    assert "gin" in search.lower() or "tsvector" in search.lower()


def test_mig_sales_attachment_vault_fk_matches_canonical_varchar36():
    """sales_attachments.vault_document_id must match vault_documents.id (VARCHAR(36))."""
    from sqlalchemy import String

    from app.models_vault import VaultDocument
    from app.sales_crm.models import SalesAttachment
    from app.sales_proposals.models import CommercialProposalVersion

    assert isinstance(VaultDocument.id.type, String)
    assert VaultDocument.id.type.length == 36
    assert isinstance(SalesAttachment.vault_document_id.type, String)
    assert SalesAttachment.vault_document_id.type.length == 36
    assert isinstance(CommercialProposalVersion.pdf_vault_document_id.type, String)
    assert CommercialProposalVersion.pdf_vault_document_id.type.length == 36

    attachment_fks = {fk.target_fullname for fk in SalesAttachment.__table__.c.vault_document_id.foreign_keys}
    proposal_fks = {
        fk.target_fullname
        for fk in CommercialProposalVersion.__table__.c.pdf_vault_document_id.foreign_keys
    }
    assert "vault_documents.id" in attachment_fks
    assert "vault_documents.id" in proposal_fks
    constraint_names = {c.name for c in SalesAttachment.__table__.constraints}
    assert "uq_sales_attachment_vault" in constraint_names

    runner = Path(__file__).resolve().parents[2] / "scripts" / "rc1" / "migrate_sql.py"
    runner_text = runner.read_text(encoding="utf-8")
    assert "elfis_sales_crm_postgres.sql" in runner_text

    render = Path(__file__).resolve().parents[3] / "render.yaml"
    assert "python -m scripts.rc1.migrate_sql" in render.read_text(encoding="utf-8")

    crm_sql = (SQL_DIR / "elfis_sales_crm_postgres.sql").read_text(encoding="utf-8")
    assert "vault_document_id VARCHAR(36) NOT NULL REFERENCES vault_documents(id)" in crm_sql
    assert "CONSTRAINT uq_sales_attachment_vault" in crm_sql
    assert "vault_document_id INTEGER" not in crm_sql

    proposals_sql = (SQL_DIR / "elfis_sales_proposals_postgres.sql").read_text(encoding="utf-8")
    assert "pdf_vault_document_id VARCHAR(36) REFERENCES vault_documents(id)" in proposals_sql
    assert "pdf_vault_document_id INTEGER" not in proposals_sql


@pytest.mark.skipif(
    not (os.getenv("ELFIS_PERFORMANCE_DATABASE_URL") or "").lower().startswith("postgres"),
    reason="PostgreSQL migration test NOT EXECUTED — set ELFIS_PERFORMANCE_DATABASE_URL",
)
def test_mig_001_upgrade_empty_postgres():
    """Placeholder : pas d’Alembic V1 — appliquer sql/*.sql manuellement en staging."""
    pytest.skip("Alembic non présent — migrations SQL manuelles (voir runbook)")
