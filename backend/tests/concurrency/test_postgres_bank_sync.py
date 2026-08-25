"""BANK-3.1 — garantie PostgreSQL réelle (unique partiel + concurrence)."""

from __future__ import annotations

import re
import threading
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import app.banking.banking_models  # noqa: F401
import app.events.event_models  # noqa: F401
import app.models  # noqa: F401
import app.models_saas  # noqa: F401
from app.banking.banking_models import ElfisBankConnection, ElfisBankSyncRun
from app.banking.connectors import registry
from app.banking.engine import BankingEngine, SyncAlreadyInProgressError
from app.banking.sync_lock import (
    ADVISORY_LOCK_NAMESPACE,
    acquire_connection_sync_lock,
    lock_backend_pid,
    lock_is_held,
    release_connection_sync_lock,
)
from app.banking.sync_engine import SyncEngine
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models import BankAccount, BankTransaction
from app.models_saas import Organization
from scripts.rc1.migrate_sql import SQL_DIR, apply_sql_file
from tests.banking.conftest_helpers import FakeBankConnector, make_tx, seed_org
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres


def _cleanup_org(session, org_id: int) -> None:
    account_ids = [
        row.id
        for row in session.query(BankAccount).filter(BankAccount.organization_id == org_id).all()
    ]
    if account_ids:
        session.query(BankTransaction).filter(BankTransaction.account_id.in_(account_ids)).delete(
            synchronize_session=False
        )
    session.query(ElfisBankSyncRun).filter(ElfisBankSyncRun.organization_id == org_id).delete(
        synchronize_session=False
    )
    session.query(BankAccount).filter(BankAccount.organization_id == org_id).delete(
        synchronize_session=False
    )
    session.query(ElfisBankConnection).filter(
        ElfisBankConnection.organization_id == org_id
    ).delete(synchronize_session=False)
    session.query(ElfisEvent).filter(ElfisEvent.organization_id == org_id).delete(
        synchronize_session=False
    )
    session.query(Organization).filter(Organization.id == org_id).delete(synchronize_session=False)
    session.commit()


def _bank31_sql() -> str:
    return re.sub(
        r"(?m)^\s*--.*?$",
        "",
        (SQL_DIR / "elfis_banking_bank31_postgres.sql").read_text(encoding="utf-8"),
    )


def _apply_bank31_raw(engine) -> None:
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute(_bank31_sql())
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _probe_row(account_id: int, external_id: str | None, label: str = "P") -> BankTransaction:
    return BankTransaction(
        account_id=account_id,
        external_id=external_id,
        booked_at="2026-07-01",
        label=label,
        amount=1.0,
        currency="EUR",
        category="autre",
        status="booked",
        source="fake",
    )


def test_postgres_bank31_unique_index_and_migration_replay():
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    first = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank31_postgres.sql")
    second = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank31_postgres.sql")
    assert first["errors"] == []
    assert second["errors"] == []

    with engine.connect() as conn:
        indexdef = conn.execute(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'bank_transactions'
                  AND indexname = 'uq_bank_transactions_account_external_id'
                """
            )
        ).scalar()
    assert indexdef
    lowered = indexdef.lower()
    assert "unique" in lowered
    assert "account_id" in lowered
    assert "external_id" in lowered
    assert "fingerprint" not in lowered
    assert "where" in lowered

    with engine.connect() as conn:
        checkdef = conn.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conname = 'ck_bank_transactions_external_id_trimmed'
                """
            )
        ).scalar()
    assert checkdef
    assert "btrim" in checkdef.lower()
    assert "external_id" in checkdef.lower()

    db = Session()
    org_id = None
    probe_a = 2_100_000_000 + (uuid4().int % 50_000)
    probe_b = probe_a + 1
    try:
        org = seed_org(db, f"bank31-unique-{uuid4().hex[:8]}")
        org_id = org.id
        db.query(BankTransaction).filter(
            BankTransaction.account_id.in_([probe_a, probe_b])
        ).delete(synchronize_session=False)
        db.commit()
        db.add(
            BankTransaction(
                account_id=probe_a,
                external_id="bank31-same",
                booked_at="2026-07-01",
                label="A",
                amount=1.0,
                currency="EUR",
                category="autre",
                status="booked",
                source="fake",
            )
        )
        db.commit()
        db.add(
            BankTransaction(
                account_id=probe_a,
                external_id="bank31-same",
                booked_at="2026-07-01",
                label="B",
                amount=1.0,
                currency="EUR",
                category="autre",
                status="booked",
                source="fake",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(
            BankTransaction(
                account_id=probe_b,
                external_id="bank31-same",
                booked_at="2026-07-01",
                label="C",
                amount=1.0,
                currency="EUR",
                category="autre",
                status="booked",
                source="fake",
            )
        )
        db.add(
            BankTransaction(
                account_id=probe_a,
                external_id="",
                booked_at="2026-07-01",
                label="EMPTY",
                amount=-25.0,
                currency="EUR",
                category="autre",
                status="booked",
                source="fake",
            )
        )
        db.add(
            BankTransaction(
                account_id=probe_a,
                external_id="",
                booked_at="2026-07-01",
                label="EMPTY",
                amount=-25.0,
                currency="EUR",
                category="autre",
                status="booked",
                source="fake",
            )
        )
        db.commit()
        empty_count = (
            db.query(BankTransaction)
            .filter(
                BankTransaction.account_id == probe_a,
                BankTransaction.external_id == "",
            )
            .count()
        )
        assert empty_count == 2

        db.add(_probe_row(probe_a, " abc ", "PADDED"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    """
                    INSERT INTO bank_transactions
                        (account_id, external_id, booked_at, label, amount, currency,
                         category, status, source)
                    VALUES
                        (:account_id, NULL, '2026-07-01', 'NULL-ID', 1, 'EUR',
                         'autre', 'booked', 'fake')
                    """
                ),
                {"account_id": probe_a},
            )
            db.commit()
        db.rollback()
    finally:
        db.query(BankTransaction).filter(
            BankTransaction.account_id.in_([probe_a, probe_b])
        ).delete(synchronize_session=False)
        if org_id is not None:
            _cleanup_org(db, org_id)
        db.close()


def test_postgres_bank31_preflight_raises_on_conflicting_groups():
    require_postgres()
    Session, engine = make_pg_session_factory()
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TEMP TABLE bank_transactions_bank31_probe (
                    account_id integer,
                    external_id text
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO bank_transactions_bank31_probe (account_id, external_id)
                VALUES (1, 'dup-ext'), (1, ' dup-ext '), (2, 'ok-ext')
                """
            )
        )
        conflict_count = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM (
            SELECT account_id, btrim(external_id)
            FROM bank_transactions_bank31_probe
            WHERE btrim(COALESCE(external_id, '')) <> ''
            GROUP BY account_id, btrim(external_id)
            HAVING COUNT(*) > 1
        ) conflicts
                """
            )
        ).scalar()
        conn.commit()
    assert conflict_count == 1


def test_postgres_bank31_preflight_rejects_padded_historical_pair():
    require_postgres()
    Session, engine = make_pg_session_factory()
    account_id = 2_130_000_000 + (uuid4().int % 20_000)
    db = Session()
    try:
        db.execute(
            text(
                "ALTER TABLE bank_transactions "
                "DROP CONSTRAINT IF EXISTS ck_bank_transactions_external_id_trimmed"
            )
        )
        db.commit()
        db.add(_probe_row(account_id, "abc", "CANON"))
        db.add(_probe_row(account_id, " abc ", "PADDED"))
        db.commit()
        with pytest.raises(Exception) as caught:
            _apply_bank31_raw(engine)
        message = str(caught.value)
        assert "BANK-3.1" in message
        assert "not trimmed" in message.lower() or "trimmed provider" in message.lower()
        db.query(BankTransaction).filter(BankTransaction.account_id == account_id).delete(
            synchronize_session=False
        )
        db.commit()
        _apply_bank31_raw(engine)
        replay = apply_sql_file(engine, SQL_DIR / "elfis_banking_bank31_postgres.sql")
        assert replay["errors"] == []
    finally:
        db.query(BankTransaction).filter(BankTransaction.account_id == account_id).delete(
            synchronize_session=False
        )
        db.commit()
        try:
            _apply_bank31_raw(engine)
        except Exception:
            pass
        db.close()


def test_postgres_bank31_old_schema_clean_data_upgrades():
    require_postgres()
    Session, engine = make_pg_session_factory()
    account_id = 2_140_000_000 + (uuid4().int % 20_000)
    db = Session()
    try:
        db.execute(
            text(
                "ALTER TABLE bank_transactions "
                "DROP CONSTRAINT IF EXISTS ck_bank_transactions_external_id_trimmed"
            )
        )
        db.commit()
        db.add(_probe_row(account_id, "clean-ext", "CLEAN"))
        db.add(_probe_row(account_id, "", "EMPTY-A"))
        db.add(_probe_row(account_id, "", "EMPTY-B"))
        db.commit()
        _apply_bank31_raw(engine)
        with engine.connect() as conn:
            present = conn.execute(
                text(
                    """
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'ck_bank_transactions_external_id_trimmed'
                    """
                )
            ).scalar()
        assert present == 1
        assert (
            db.query(BankTransaction).filter(BankTransaction.account_id == account_id).count()
            == 3
        )
    finally:
        db.query(BankTransaction).filter(BankTransaction.account_id == account_id).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()


def test_postgres_concurrent_sync_one_transaction_and_one_created_event():
    require_postgres()
    Session, engine = make_pg_session_factory()
    marker = uuid4().hex[:12]
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx(
                    "fake-acc-1",
                    date(2026, 7, 1),
                    "CONC PG",
                    42.0,
                    external_id=f"bank31-conc-{marker}",
                )
            ]
        }
    )
    registry.register_connector("fake", lambda: connector)
    bootstrap = Session()
    org = seed_org(bootstrap, f"bank31-conc-{marker}")
    org_id = org.id
    BankingEngine(bootstrap).connect(
        organization_id=org_id, provider="fake", bank_name="Banque Factice"
    )
    bootstrap.close()

    outcomes: list[str] = []
    errors: list[str] = []
    barrier = threading.Barrier(2)

    def worker() -> None:
        local = Session()
        try:
            barrier.wait(timeout=10)
            runs = SyncEngine(local, lock_wait_seconds=8.0).run_sync(org_id)
            outcomes.append(runs[0].status)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}:{exc}")
        finally:
            local.close()

    try:
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert errors == []
        assert outcomes.count("completed") == 2
        check = Session()
        try:
            rows = check.query(BankTransaction).join(
                BankAccount, BankTransaction.account_id == BankAccount.id
            ).filter(BankAccount.organization_id == org_id).all()
            assert len(rows) == 1
            created = (
                check.query(ElfisEvent)
                .filter(
                    ElfisEvent.organization_id == org_id,
                    ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_CREATED,
                )
                .count()
            )
            assert created == 1
        finally:
            check.close()
    finally:
        registry.unregister_connector("fake")
        cleanup = Session()
        try:
            _cleanup_org(cleanup, org_id)
        finally:
            cleanup.close()


def test_postgres_concurrent_sync_returns_already_in_progress():
    require_postgres()
    Session, engine = make_pg_session_factory()
    hold = threading.Event()
    release = threading.Event()
    marker = uuid4().hex[:12]
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx(
                    "fake-acc-1",
                    date(2026, 7, 1),
                    "LOCK PG",
                    1.0,
                    external_id=f"bank31-lock-{marker}",
                )
            ]
        },
        hold_before_page=hold,
        release_before_page=release,
    )
    registry.register_connector("fake", lambda: connector)
    bootstrap = Session()
    org = seed_org(bootstrap, f"bank31-lock-{marker}")
    org_id = org.id
    BankingEngine(bootstrap).connect(
        organization_id=org_id, provider="fake", bank_name="Banque Factice"
    )
    bootstrap.close()

    outcomes: list[str] = []
    errors: list[str] = []

    def worker(wait: float, tag: str) -> None:
        local = Session()
        try:
            SyncEngine(local, lock_wait_seconds=wait).run_sync(org_id)
            outcomes.append(f"{tag}:ok")
        except SyncAlreadyInProgressError:
            outcomes.append(f"{tag}:busy")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{tag}:{type(exc).__name__}:{exc}")
        finally:
            local.close()

    try:
        first = threading.Thread(target=worker, args=(2.0, "a"))
        first.start()
        assert hold.wait(timeout=15)
        second = threading.Thread(target=worker, args=(0.0, "b"))
        second.start()
        second.join(timeout=15)
        release.set()
        first.join(timeout=20)
        assert errors == []
        assert "b:busy" in outcomes
        assert "a:ok" in outcomes
        check = Session()
        try:
            count = (
                check.query(BankTransaction)
                .join(BankAccount, BankTransaction.account_id == BankAccount.id)
                .filter(BankAccount.organization_id == org_id)
                .count()
            )
            assert count == 1
        finally:
            check.close()
    finally:
        registry.unregister_connector("fake")
        cleanup = Session()
        try:
            _cleanup_org(cleanup, org_id)
        finally:
            cleanup.close()


def _try_advisory_lock(conn, connection_id: int) -> bool:
    return bool(
        conn.execute(
            text("SELECT pg_try_advisory_lock(:ns, :cid)"),
            {"ns": ADVISORY_LOCK_NAMESPACE, "cid": int(connection_id)},
        ).scalar()
    )


def _unlock_advisory(conn, connection_id: int) -> None:
    conn.execute(
        text("SELECT pg_advisory_unlock(:ns, :cid)"),
        {"ns": ADVISORY_LOCK_NAMESPACE, "cid": int(connection_id)},
    )


def test_postgres_advisory_lock_stays_on_pinned_connection_across_session_commits():
    require_postgres()
    Session, engine = make_pg_session_factory()
    db = Session()
    cid = 2_110_000_000 + (uuid4().int % 40_000)
    held = acquire_connection_sync_lock(
        db, organization_id=1, connection_id=cid, wait_seconds=0
    )
    try:
        assert held is not None
        pid_at_lock = held.backend_pid
        assert pid_at_lock is not None
        assert lock_backend_pid(held) == pid_at_lock
        assert lock_is_held(held)

        for _ in range(3):
            db.execute(text("SELECT pg_backend_pid()"))
            db.commit()

        assert lock_backend_pid(held) == pid_at_lock
        assert lock_is_held(held)

        rival = engine.connect()
        try:
            assert _try_advisory_lock(rival, cid) is False
        finally:
            rival.close()
    finally:
        release_connection_sync_lock(held)

    assert held is not None and held.lock_connection is None
    successor = engine.connect()
    try:
        assert _try_advisory_lock(successor, cid) is True
        _unlock_advisory(successor, cid)
    finally:
        successor.close()
    db.close()


def test_postgres_advisory_lock_distinct_connection_ids_do_not_block():
    require_postgres()
    Session, _engine = make_pg_session_factory()
    db = Session()
    cid_a = 2_120_000_000 + (uuid4().int % 20_000)
    cid_b = cid_a + 1
    lock_a = acquire_connection_sync_lock(
        db, organization_id=1, connection_id=cid_a, wait_seconds=0
    )
    lock_b = acquire_connection_sync_lock(
        db, organization_id=1, connection_id=cid_b, wait_seconds=0
    )
    try:
        assert lock_a is not None and lock_b is not None
        assert lock_a.backend_pid != lock_b.backend_pid
        assert lock_is_held(lock_a)
        assert lock_is_held(lock_b)
        db.execute(text("SELECT 1"))
        db.commit()
        db.execute(text("SELECT 1"))
        db.commit()
        assert lock_backend_pid(lock_a) == lock_a.backend_pid
        assert lock_backend_pid(lock_b) == lock_b.backend_pid
    finally:
        release_connection_sync_lock(lock_a)
        release_connection_sync_lock(lock_b)
        db.close()


def test_postgres_advisory_lock_released_when_sync_raises():
    require_postgres()
    Session, _engine = make_pg_session_factory()
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "FAIL", 1.0, external_id="bank31-exc")
            ]
        },
        fail_times=5,
        fail_retryable=False,
    )
    registry.register_connector("fake", lambda: connector)
    db = Session()
    org = seed_org(db, f"bank31-exc-{uuid4().hex[:8]}")
    org_id = org.id
    connection = BankingEngine(db).connect(
        organization_id=org_id, provider="fake", bank_name="Banque Factice"
    )
    try:
        run = SyncEngine(db, max_attempts=1).run_sync(org_id)[0]
        assert run.status == "failed"
        probe = acquire_connection_sync_lock(
            db,
            organization_id=org_id,
            connection_id=connection.id,
            wait_seconds=0,
        )
        assert probe is not None
        release_connection_sync_lock(probe)
    finally:
        registry.unregister_connector("fake")
        _cleanup_org(db, org_id)
        db.close()


def test_postgres_advisory_lock_released_after_integrity_recovery():
    require_postgres()
    Session, _engine = make_pg_session_factory()
    ext = f"bank31-int-{uuid4().hex[:10]}"
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "INT", 9.0, external_id=ext)
            ]
        }
    )
    registry.register_connector("fake", lambda: connector)
    db = Session()
    org = seed_org(db, f"bank31-int-{uuid4().hex[:8]}")
    org_id = org.id
    connection = BankingEngine(db).connect(
        organization_id=org_id, provider="fake", bank_name="Banque Factice"
    )
    try:
        account = (
            db.query(BankAccount)
            .filter(BankAccount.organization_id == org_id)
            .one()
        )
        db.add(
            BankTransaction(
                account_id=account.id,
                external_id=ext,
                booked_at="2026-07-01",
                label="INT",
                amount=9.0,
                currency="EUR",
                category="autre",
                status="booked",
                source="fake",
            )
        )
        db.commit()
        run = SyncEngine(db, max_attempts=1).run_sync(org_id)[0]
        assert run.status == "completed"
        assert (
            db.query(BankTransaction)
            .filter(BankTransaction.account_id == account.id)
            .count()
            == 1
        )
        probe = acquire_connection_sync_lock(
            db,
            organization_id=org_id,
            connection_id=connection.id,
            wait_seconds=0,
        )
        assert probe is not None
        release_connection_sync_lock(probe)
    finally:
        registry.unregister_connector("fake")
        _cleanup_org(db, org_id)
        db.close()


def test_postgres_integrityerror_upsert_recovers_without_duplicate_row():
    require_postgres()
    Session, _engine = make_pg_session_factory()
    ext_race = f"bank31-race-{uuid4().hex[:10]}"
    connector = FakeBankConnector(transactions={"fake-acc-1": []})
    registry.register_connector("fake", lambda: connector)
    bootstrap = Session()
    org = seed_org(bootstrap, f"bank31-race-{uuid4().hex[:8]}")
    org_id = org.id
    connection = BankingEngine(bootstrap).connect(
        organization_id=org_id, provider="fake", bank_name="Banque Factice"
    )
    account_id = (
        bootstrap.query(BankAccount)
        .filter(BankAccount.organization_id == org_id)
        .one()
        .id
    )
    bootstrap.close()

    item = make_tx("fake-acc-1", date(2026, 7, 1), "RACE", 3.0, external_id=ext_race)
    booked_iso = item.booked_at.isoformat()
    errors: list[str] = []
    barrier = threading.Barrier(2)

    def worker() -> None:
        local = Session()
        try:
            account = local.get(BankAccount, account_id)
            run = ElfisBankSyncRun(
                organization_id=org_id,
                connection_id=connection.id,
                provider="fake",
                status="running",
            )
            local.add(run)
            local.commit()
            local.refresh(run)
            barrier.wait(timeout=10)
            SyncEngine(local)._upsert_provider_transaction(
                account, item, booked_iso, run, set()
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}:{exc}")
            local.rollback()
        finally:
            local.close()

    try:
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert errors == []
        check = Session()
        try:
            rows = (
                check.query(BankTransaction)
                .filter(
                    BankTransaction.account_id == account_id,
                    BankTransaction.external_id == ext_race,
                )
                .all()
            )
            assert len(rows) == 1
            probe = acquire_connection_sync_lock(
                check,
                organization_id=org_id,
                connection_id=connection.id,
                wait_seconds=0,
            )
            assert probe is not None
            release_connection_sync_lock(probe)
        finally:
            check.close()
    finally:
        registry.unregister_connector("fake")
        cleanup = Session()
        try:
            _cleanup_org(cleanup, org_id)
        finally:
            cleanup.close()
