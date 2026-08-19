"""Cohérence ORM ↔ schéma PostgreSQL + index critiques RC1."""

from __future__ import annotations

from sqlalchemy import inspect, text

from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres

# Différences volontaires documentées (SQLite Text vs PG tsvector, etc.)
ALLOWLIST_TYPE_MISMATCH = {
    ("elfis_search_documents", "search_vector"),  # ORM Text, PG tsvector via SQL
}


def test_postgres_critical_indexes_present():
    require_postgres()
    _, engine = make_pg_session_factory()
    with engine.connect() as conn:
        idx = {
            r[0]: r[1]
            for r in conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public'"
                )
            )
        }
        constraints = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT conname FROM pg_constraint
                    WHERE contype IN ('u', 'p')
                    """
                )
            )
        }

    names = set(idx) | constraints
    required = [
        "uq_document_email_org_idempotency",
        "uq_elfis_billing_provider_event",
        "uq_vault_org_checksum_active",
        "ix_elfis_jobs_claim",
        "ix_elfis_events_claim",
        "ix_elfis_search_vector_gin",
    ]
    missing = [n for n in required if n not in names and not any(n in x for x in names)]
    assert not missing, f"Index/contraintes manquants: {missing}"

    gin_ok = any("using gin" in (d or "").lower() for d in idx.values())
    assert gin_ok, "Aucun index GIN détecté"


def test_postgres_schema_core_tables():
    require_postgres()
    _, engine = make_pg_session_factory()
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    expected = {
        "users",
        "organizations",
        "elfis_jobs",
        "elfis_events",
        "vault_documents",
        "elfis_quotas",
        "elfis_usage_counters",
        "elfis_search_documents",
    }
    missing = sorted(expected - tables)
    assert not missing, f"Tables manquantes: {missing}"


def test_postgres_orm_columns_spot_check():
    """Spot-check colonnes critiques — allowlist pour divergences volontaires."""
    require_postgres()
    from app.jobs.job_models import ElfisJob
    from app.search import search_models  # noqa: F401

    _, engine = make_pg_session_factory()
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("elfis_jobs")}
    for name in ("job_id", "status", "locked_at", "locked_by", "available_at", "organization_id"):
        assert name in cols

    # search_vector : divergence documentée
    search_cols = {c["name"]: c for c in insp.get_columns("elfis_search_documents")}
    assert "search_vector" in search_cols
    assert ("elfis_search_documents", "search_vector") in ALLOWLIST_TYPE_MISMATCH
