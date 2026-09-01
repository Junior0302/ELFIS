"""BANK-5 — PostgreSQL réel : migration additive, replay, conservation des données."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

import app.banking.banking_models  # noqa: F401
import app.events.event_models  # noqa: F401
import app.jobs.job_models  # noqa: F401
import app.models  # noqa: F401
import app.models_saas  # noqa: F401
from app.banking.banking_models import ElfisBankConnection
from app.banking.consent import consent_status, needs_reauth
from scripts.rc1.migrate_sql import SQL_DIR, apply_sql_file
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres


def _sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def _probe_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def test_bank5_sql_has_no_destructive_statements():
    sql = _sql("elfis_banking_bank5_postgres.sql").lower()
    assert "delete from" not in sql
    assert "drop table" not in sql
    assert "drop column" not in sql
    assert "truncate" not in sql
    assert "authentication_expires_at" in sql
    assert "reauth_required_at" in sql
    assert "reauth_reason" in sql
    assert "last_reauth_at" in sql


def test_bank5_fresh_schema_and_replay():
    require_postgres()
    factory, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"
    first = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank5_postgres.sql")
    second = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank5_postgres.sql")
    assert first["errors"] == []
    assert second["errors"] == []
    session = factory()
    try:
        cols = {
            row[0]
            for row in session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'elfis_bank_connections'"
                )
            )
        }
        assert "authentication_expires_at" in cols
        assert "reauth_required_at" in cols
        assert "reauth_reason" in cols
        assert "last_reauth_at" in cols
        assert "last_sync_status" in cols
    finally:
        session.close()


def test_bank4_then_bank5_preserves_existing_connections():
    require_postgres()
    factory, engine = make_pg_session_factory()
    bank4 = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    bank5 = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank5_postgres.sql")
    assert bank4["errors"] == []
    assert bank5["errors"] == []
    session = factory()
    probe_name = _probe_id("bank5-preserve")
    try:
        row = ElfisBankConnection(
            organization_id=1,
            provider="bridge",
            provider_connection_id=probe_name,
            bank_name=probe_name,
            status="connected",
            last_sync_status="success",
            consecutive_sync_failures=2,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        row_id = row.id
        replay = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank5_postgres.sql")
        assert replay["errors"] == []
        session.expire_all()
        kept = session.get(ElfisBankConnection, row_id)
        assert kept is not None
        assert kept.bank_name == probe_name
        assert kept.consecutive_sync_failures == 2
        assert kept.last_sync_status == "success"
        assert kept.authentication_expires_at is None
        assert kept.reauth_reason is None
        assert needs_reauth(kept) is False
        assert consent_status(kept) == "valid"
    finally:
        session.query(ElfisBankConnection).filter(
            ElfisBankConnection.provider_connection_id == probe_name
        ).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_bank5_consent_columns_roundtrip_postgres():
    require_postgres()
    factory, engine = make_pg_session_factory()
    apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    apply_sql_file(engine, SQL_DIR / "elfis_banking_bank5_postgres.sql")
    session = factory()
    probe = _probe_id("pg-consent")
    expires = datetime(2026, 8, 20, 12, 0, 0)
    try:
        row = ElfisBankConnection(
            organization_id=1,
            provider="bridge",
            provider_connection_id=probe,
            bank_name="PG",
            status="connected",
            authentication_expires_at=expires,
            reauth_required_at=expires,
            reauth_reason="consent_expired",
            last_reauth_at=expires - timedelta(days=180),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.authentication_expires_at == expires
        assert row.reauth_reason == "consent_expired"
        assert row.last_reauth_at is not None
        assert needs_reauth(row, now=datetime(2026, 8, 27, 12, 0, 0)) is True
        assert consent_status(row, now=datetime(2026, 8, 27, 12, 0, 0)) == "reauth_required"
    finally:
        session.query(ElfisBankConnection).filter(
            ElfisBankConnection.provider_connection_id == probe
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
