"""BANK-4 — PostgreSQL réel : migration, unique receipts, concurrence."""

from __future__ import annotations

import threading
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import app.banking.banking_models  # noqa: F401
import app.events.event_models  # noqa: F401
import app.jobs.job_models  # noqa: F401
import app.models  # noqa: F401
import app.models_saas  # noqa: F401
from app.banking.banking_models import ElfisBankConnection, ElfisBankWebhookReceipt
from scripts.rc1.migrate_sql import SQL_DIR, apply_sql_file
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres


def _sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def _probe_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def test_bank4_sql_has_no_destructive_statements():
    sql = _sql("elfis_banking_bank4_postgres.sql").lower()
    assert "delete from" not in sql
    assert "drop table" not in sql
    assert "drop column" not in sql
    assert "truncate" not in sql


def test_bank4_fresh_schema_and_replay():
    require_postgres()
    factory, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"
    first = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    second = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
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
        assert "last_sync_started_at" in cols
        assert "last_sync_status" in cols
        assert "last_sync_error_code" in cols
        assert "consecutive_sync_failures" in cols
        indexdef = session.execute(
            text(
                """
                SELECT indexdef FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'uq_elfis_bank_webhook_provider_event'
                """
            )
        ).scalar()
        assert indexdef
        assert "unique" in indexdef.lower()
        assert "provider" in indexdef.lower()
        assert "provider_event_id" in indexdef.lower()
        session.execute(text("SELECT 1 FROM elfis_bank_webhook_receipts LIMIT 1"))
    finally:
        session.close()


def test_bank31_then_bank4_preserves_existing_connections():
    require_postgres()
    factory, engine = make_pg_session_factory()
    bank31 = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank31_postgres.sql")
    bank4 = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    assert bank31["errors"] == []
    assert bank4["errors"] == []
    session = factory()
    probe_name = _probe_id("bank4-preserve")
    try:
        row = ElfisBankConnection(
            organization_id=1,
            provider="bridge",
            provider_connection_id=probe_name,
            bank_name=probe_name,
            status="connected",
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        row_id = row.id
        before = session.query(ElfisBankConnection).filter(
            ElfisBankConnection.provider_connection_id == probe_name
        ).count()
        replay = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
        assert replay["errors"] == []
        session.expire_all()
        after = session.query(ElfisBankConnection).filter(
            ElfisBankConnection.provider_connection_id == probe_name
        ).count()
        kept = session.get(ElfisBankConnection, row_id)
        assert before == 1
        assert after == 1
        assert kept is not None
        assert kept.bank_name == probe_name
        assert kept.last_sync_status in {"never", "queued", "syncing", "success", "failed"}
    finally:
        session.query(ElfisBankConnection).filter(
            ElfisBankConnection.provider_connection_id == probe_name
        ).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_bank4_adds_columns_when_missing_on_disposable_db():
    """Simule un schéma connexions pré-BANK-4 via une table probe (pas de DROP métier)."""
    require_postgres()
    factory, engine = make_pg_session_factory()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS elfis_bank_connections_pre_bank4"))
        conn.execute(
            text(
                """
                CREATE TABLE elfis_bank_connections_pre_bank4 (
                    id SERIAL PRIMARY KEY,
                    organization_id INTEGER NOT NULL,
                    provider VARCHAR(32) NOT NULL,
                    provider_connection_id VARCHAR(128) DEFAULT '',
                    bank_name VARCHAR(255) DEFAULT '',
                    status VARCHAR(32) DEFAULT 'connected',
                    error_message TEXT,
                    last_sync_at TIMESTAMP,
                    next_sync_at TIMESTAMP,
                    sync_interval_minutes INTEGER DEFAULT 1440,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO elfis_bank_connections_pre_bank4 "
                "(organization_id, provider, provider_connection_id, bank_name) "
                "VALUES (1, 'bridge', 'pre-bank4', 'Kept')"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE elfis_bank_connections_pre_bank4 "
                "ADD COLUMN IF NOT EXISTS last_sync_started_at TIMESTAMP"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE elfis_bank_connections_pre_bank4 "
                "ADD COLUMN IF NOT EXISTS last_sync_status VARCHAR(16) NOT NULL DEFAULT 'never'"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE elfis_bank_connections_pre_bank4 "
                "ADD COLUMN IF NOT EXISTS last_sync_error_code VARCHAR(64)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE elfis_bank_connections_pre_bank4 "
                "ADD COLUMN IF NOT EXISTS consecutive_sync_failures INTEGER NOT NULL DEFAULT 0"
            )
        )
    session = factory()
    try:
        kept = session.execute(
            text(
                "SELECT bank_name, last_sync_status, consecutive_sync_failures "
                "FROM elfis_bank_connections_pre_bank4 WHERE provider_connection_id = 'pre-bank4'"
            )
        ).one()
        assert kept[0] == "Kept"
        assert kept[1] == "never"
        assert kept[2] == 0
    finally:
        session.execute(text("DROP TABLE IF EXISTS elfis_bank_connections_pre_bank4"))
        session.commit()
        session.close()


def test_webhook_receipt_unique_and_provider_isolation():
    require_postgres()
    factory, engine = make_pg_session_factory()
    apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    session = factory()
    event_id = _probe_id("evt")[:64].ljust(64, "a")
    other = _probe_id("evt2")[:64].ljust(64, "b")
    try:
        session.add(
            ElfisBankWebhookReceipt(
                provider="bridge",
                provider_event_id=event_id,
                event_type="item.refreshed",
                payload_hash=event_id,
                status="queued",
            )
        )
        session.commit()
        session.add(
            ElfisBankWebhookReceipt(
                provider="bridge",
                provider_event_id=event_id,
                event_type="item.refreshed",
                payload_hash=event_id,
                status="received",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(
            ElfisBankWebhookReceipt(
                provider="powens",
                provider_event_id=event_id,
                event_type="item.refreshed",
                payload_hash=event_id,
                status="received",
            )
        )
        session.commit()
        other = _probe_id("evt2")[:64].ljust(64, "b")
        session.add(
            ElfisBankWebhookReceipt(
                provider="bridge",
                provider_event_id=other,
                event_type="item.refreshed",
                payload_hash=other,
                status="received",
            )
        )
        session.commit()
        n_bridge = (
            session.query(ElfisBankWebhookReceipt)
            .filter(ElfisBankWebhookReceipt.provider == "bridge")
            .filter(ElfisBankWebhookReceipt.provider_event_id.in_([event_id, other]))
            .count()
        )
        n_powens = (
            session.query(ElfisBankWebhookReceipt)
            .filter(ElfisBankWebhookReceipt.provider == "powens")
            .filter(ElfisBankWebhookReceipt.provider_event_id == event_id)
            .count()
        )
        assert n_bridge == 2
        assert n_powens == 1
    finally:
        session.query(ElfisBankWebhookReceipt).filter(
            ElfisBankWebhookReceipt.provider_event_id.in_([event_id, other])
        ).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_concurrent_same_receipt_inserts_one_row():
    require_postgres()
    factory, engine = make_pg_session_factory()
    apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    event_id = _probe_id("conc")
    event_id = event_id[:64].ljust(64, "c")
    errors: list[str] = []
    wins: list[int] = []

    def _insert() -> None:
        db = factory()
        try:
            db.add(
                ElfisBankWebhookReceipt(
                    provider="bridge",
                    provider_event_id=event_id,
                    event_type="item.refreshed",
                    payload_hash=event_id,
                    status="received",
                )
            )
            db.commit()
            wins.append(1)
        except IntegrityError:
            db.rollback()
            errors.append("integrity")
        finally:
            db.close()

    t1 = threading.Thread(target=_insert)
    t2 = threading.Thread(target=_insert)
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)
    session = factory()
    try:
        count = (
            session.query(ElfisBankWebhookReceipt)
            .filter(
                ElfisBankWebhookReceipt.provider == "bridge",
                ElfisBankWebhookReceipt.provider_event_id == event_id,
            )
            .count()
        )
        assert count == 1
        assert len(wins) + len(errors) == 2
        assert len(wins) >= 1
    finally:
        session.query(ElfisBankWebhookReceipt).filter(
            ElfisBankWebhookReceipt.provider_event_id == event_id
        ).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_sync_status_columns_roundtrip_postgres():
    require_postgres()
    factory, engine = make_pg_session_factory()
    apply_sql_file(engine, SQL_DIR / "elfis_banking_bank4_postgres.sql")
    session = factory()
    probe = _probe_id("pg-item")
    try:
        row = ElfisBankConnection(
            organization_id=1,
            provider="bridge",
            provider_connection_id=probe,
            bank_name="PG",
            status="connected",
            last_sync_status="failed",
            last_sync_error_code="timeout",
            consecutive_sync_failures=2,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.last_sync_status == "failed"
        assert row.consecutive_sync_failures == 2
    finally:
        session.query(ElfisBankConnection).filter(
            ElfisBankConnection.provider_connection_id == probe
        ).delete(synchronize_session=False)
        session.commit()
        session.close()
