"""Tests Sync Engine — import initial, incrémental, doublons, retry, reprise."""

from __future__ import annotations

from datetime import date

import pytest

from app.banking.banking_types import NormalizedAccount
from app.banking.connectors import registry
from app.banking.engine import BankingEngine
from app.banking.sync_engine import SyncEngine
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models import BankTransaction

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_db,
    make_tx,
    seed_org,
)


def _register(connector: FakeBankConnector):
    registry.register_connector("fake", lambda: connector)


@pytest.fixture(autouse=True)
def _cleanup_registry():
    yield
    registry.unregister_connector("fake")


def _setup(connector: FakeBankConnector):
    db = make_banking_db()
    org = seed_org(db)
    _register(connector)
    connection = BankingEngine(db).connect(
        organization_id=org.id, provider="fake", bank_name="Banque Factice"
    )
    return db, org, connection


BASE_TXS = [
    make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT CLIENT ALPHA", 500.0),
    make_tx("fake-acc-1", date(2026, 7, 3), "LOYER BUREAUX", -900.0),
    make_tx("fake-acc-1", date(2026, 7, 5), "GOOGLE ADS", -120.0),
]


def test_initial_import_creates_normalized_transactions_and_journal():
    connector = FakeBankConnector(transactions={"fake-acc-1": list(BASE_TXS)})
    db, org, connection = _setup(connector)

    runs = SyncEngine(db).run_sync(org.id)
    assert len(runs) == 1
    run = runs[0]
    assert run.status == "completed"
    assert run.sync_type == "initial"
    assert run.transactions_created == 3
    assert run.duplicates_skipped == 0
    assert run.cursor == "2026-07-05"
    assert run.duration_ms is not None

    txs = db.query(BankTransaction).order_by(BankTransaction.booked_at.asc()).all()
    assert len(txs) == 3
    # Normalisation : date ISO, source fournisseur, statut, catégorie auto
    assert txs[0].booked_at == "2026-07-01"
    assert all(t.source == "fake" for t in txs)
    assert all(t.status == "booked" for t in txs)
    assert txs[1].category == "loyer"
    assert txs[2].category == "publicite"

    created_events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_CREATED)
        .count()
    )
    assert created_events == 3
    completed = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_SYNC_COMPLETED)
        .one()
    )
    assert completed.payload["transactions_created"] == 3

    db.refresh(connection)
    assert connection.last_sync_at is not None
    assert connection.next_sync_at is not None


def test_incremental_sync_only_imports_new_transactions():
    connector = FakeBankConnector(transactions={"fake-acc-1": list(BASE_TXS)})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)

    # Nouvelle opération côté fournisseur
    connector.transactions["fake-acc-1"].append(
        make_tx("fake-acc-1", date(2026, 7, 10), "ENCAISSEMENT STRIPE", 320.0)
    )
    runs = engine.run_sync(org.id)
    run = runs[0]
    assert run.sync_type == "incremental"
    assert run.transactions_created == 1
    assert run.cursor == "2026-07-10"
    assert db.query(BankTransaction).count() == 4


def test_resync_detects_duplicates_and_creates_nothing():
    connector = FakeBankConnector(transactions={"fake-acc-1": list(BASE_TXS)})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)

    # Le fournisseur renvoie tout l'historique (pas de since honoré) :
    # on force en vidant le curseur via un connecteur sans filtrage
    connector.transactions["fake-acc-1"] = list(BASE_TXS)
    runs = engine.run_sync(org.id)
    run = runs[0]
    assert run.status == "completed"
    assert run.transactions_created == 0
    assert db.query(BankTransaction).count() == 3


def test_two_real_transactions_same_fingerprint_keep_both_rows():
    twin = make_tx(
        "fake-acc-1",
        date(2026, 7, 1),
        "VIREMENT CLIENT ALPHA",
        500.0,
        external_id="autre-id-fournisseur",
    )
    connector = FakeBankConnector(
        transactions={"fake-acc-1": [BASE_TXS[0], twin]}
    )
    db, org, _ = _setup(connector)
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.transactions_created == 2
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    assert {r.external_id for r in rows} == {BASE_TXS[0].external_id, "autre-id-fournisseur"}
    assert sum(1 for r in rows if r.is_duplicate) == 1


def test_transaction_update_publishes_updated_event():
    connector = FakeBankConnector(transactions={"fake-acc-1": [BASE_TXS[0]]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)

    corrected = BASE_TXS[0].model_copy(update={"label": "VIREMENT CLIENT ALPHA CORRIGE"})
    connector.transactions["fake-acc-1"] = [corrected]
    run = engine.run_sync(org.id)[0]
    assert run.transactions_updated == 1
    assert db.query(BankTransaction).count() == 1
    assert db.query(BankTransaction).one().label == "VIREMENT CLIENT ALPHA CORRIGE"
    updated_events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_UPDATED)
        .count()
    )
    assert updated_events == 1


def test_retry_recovers_after_transient_provider_failure():
    connector = FakeBankConnector(
        transactions={"fake-acc-1": list(BASE_TXS)},
        fail_times=2,
        fail_retryable=True,
    )
    db, org, _ = _setup(connector)
    run = SyncEngine(db, max_attempts=3).run_sync(org.id)[0]
    assert run.status == "completed"
    assert run.attempt_count == 3
    assert run.transactions_created == 3


def test_non_retryable_failure_fails_immediately():
    connector = FakeBankConnector(
        transactions={"fake-acc-1": list(BASE_TXS)},
        fail_times=5,
        fail_retryable=False,
    )
    db, org, connection = _setup(connector)
    run = SyncEngine(db, max_attempts=3).run_sync(org.id)[0]
    assert run.status == "failed"
    assert run.attempt_count == 1
    db.refresh(connection)
    assert connection.status == "error"
    assert connection.error_message


def test_exhausted_retries_marks_run_failed_and_publishes_event():
    connector = FakeBankConnector(
        transactions={"fake-acc-1": list(BASE_TXS)},
        fail_times=10,
        fail_retryable=True,
    )
    db, org, connection = _setup(connector)
    run = SyncEngine(db, max_attempts=3).run_sync(org.id)[0]
    assert run.status == "failed"
    assert run.attempt_count == 3
    failed_event = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_SYNC_FAILED)
        .one()
    )
    assert failed_event.payload["run_id"] == run.id
    db.refresh(connection)
    assert connection.status == "error"


def test_resume_after_failure_uses_cursor_and_completes():
    accounts = [
        NormalizedAccount(external_id="fake-acc-1", label="Compte 1", balance=100.0),
        NormalizedAccount(external_id="fake-acc-2", label="Compte 2", balance=200.0),
    ]
    txs_acc2 = [make_tx("fake-acc-2", date(2026, 7, 8), "SALAIRE ASSISTANTE", -1900.0)]
    connector = FakeBankConnector(
        accounts=accounts,
        transactions={"fake-acc-1": list(BASE_TXS), "fake-acc-2": txs_acc2},
        fail_times=10,
        fail_retryable=True,
        fail_on_account="fake-acc-2",  # le compte 1 passe, le compte 2 échoue
    )
    db, org, connection = _setup(connector)
    engine = SyncEngine(db, max_attempts=2)

    failed_run = engine.run_sync(org.id)[0]
    assert failed_run.status == "failed"
    # Progrès partiel journalisé : curseur posé après le compte 1
    assert failed_run.cursor == "2026-07-05"
    assert db.query(BankTransaction).count() == 3  # compte 1 importé malgré l'échec

    # Le fournisseur est réparé : la reprise repart du curseur
    connector.fail_times = 0
    resumed_run = engine.run_sync(org.id)[0]
    assert resumed_run.status == "completed"
    assert resumed_run.resumed_from_cursor is True
    assert resumed_run.transactions_created == 1  # uniquement le compte 2
    assert db.query(BankTransaction).count() == 4
    db.refresh(connection)
    assert connection.status == "connected"
    assert connection.error_message is None


def test_sync_journal_is_persisted_and_listable():
    connector = FakeBankConnector(transactions={"fake-acc-1": list(BASE_TXS)})
    db, org, connection = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    engine.run_sync(org.id)
    runs = engine.list_runs(org.id)
    assert len(runs) == 2
    assert runs[0].sync_type == "incremental"
    assert runs[1].sync_type == "initial"
    scoped = engine.list_runs(org.id, connection_id=connection.id)
    assert len(scoped) == 2


def test_sync_without_connection_raises():
    db = make_banking_db()
    org = seed_org(db)
    from app.banking.engine import BankingEngineError

    with pytest.raises(BankingEngineError):
        SyncEngine(db).run_sync(org.id)


def test_same_provider_id_synced_twice_is_one_row():
    connector = FakeBankConnector(transactions={"fake-acc-1": [BASE_TXS[0]]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    engine.run_sync(org.id)
    assert db.query(BankTransaction).count() == 1


def test_pending_to_booked_same_id_updates():
    from app.banking.banking_types import TransactionStatus

    pending = make_tx(
        "fake-acc-1",
        date(2026, 7, 1),
        "PAIEMENT CARTE",
        -25.0,
        status=TransactionStatus.pending,
        external_id="card-1",
    )
    connector = FakeBankConnector(transactions={"fake-acc-1": [pending]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    assert db.query(BankTransaction).one().status == "pending"

    connector.transactions["fake-acc-1"] = [
        pending.model_copy(update={"status": TransactionStatus.booked})
    ]
    run = engine.run_sync(org.id)[0]
    assert run.transactions_created == 0
    assert run.transactions_updated == 1
    assert db.query(BankTransaction).count() == 1
    assert db.query(BankTransaction).one().status == "booked"
    updated = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_UPDATED)
        .count()
    )
    created = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_CREATED)
        .count()
    )
    assert updated == 1
    assert created == 1


def test_pending_and_booked_different_ids_are_not_merged():
    from app.banking.banking_types import TransactionStatus

    pending = make_tx(
        "fake-acc-1",
        date(2026, 7, 1),
        "RESTAURANT",
        -25.0,
        status=TransactionStatus.pending,
        external_id="pend-1",
    )
    booked = make_tx(
        "fake-acc-1",
        date(2026, 7, 1),
        "RESTAURANT",
        -25.0,
        status=TransactionStatus.booked,
        external_id="book-1",
    )
    connector = FakeBankConnector(transactions={"fake-acc-1": [pending, booked]})
    db, org, _ = _setup(connector)
    SyncEngine(db).run_sync(org.id)
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    assert {r.external_id for r in rows} == {"pend-1", "book-1"}


def test_same_external_id_isolated_by_account():
    accounts = [
        NormalizedAccount(external_id="fake-acc-1", label="A", balance=1.0),
        NormalizedAccount(external_id="fake-acc-2", label="B", balance=2.0),
    ]
    tx_a = make_tx("fake-acc-1", date(2026, 7, 1), "X", 10.0, external_id="shared-id")
    tx_b = make_tx("fake-acc-2", date(2026, 7, 1), "X", 10.0, external_id="shared-id")
    connector = FakeBankConnector(
        accounts=accounts,
        transactions={"fake-acc-1": [tx_a], "fake-acc-2": [tx_b]},
    )
    db, org, _ = _setup(connector)
    SyncEngine(db).run_sync(org.id)
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    assert len({r.account_id for r in rows}) == 2
    assert all(r.external_id == "shared-id" for r in rows)


def test_same_external_id_isolated_by_organization():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "X", 10.0, external_id="shared-id")
            ]
        }
    )
    db = make_banking_db()
    org_a = seed_org(db, "A")
    org_b = seed_org(db, "B")
    _register(connector)
    BankingEngine(db).connect(organization_id=org_a.id, provider="fake", bank_name="A")
    BankingEngine(db).connect(organization_id=org_b.id, provider="fake", bank_name="B")
    SyncEngine(db).run_sync(org_a.id)
    SyncEngine(db).run_sync(org_b.id)
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    accounts = {r.account_id for r in rows}
    assert len(accounts) == 2


def test_pagination_three_pages_imports_all():
    txs = [
        make_tx("fake-acc-1", date(2026, 7, d), f"OP {d}", -d * 1.0, external_id=f"p-{d}")
        for d in range(1, 7)
    ]
    connector = FakeBankConnector(transactions={"fake-acc-1": txs}, page_size=2)
    db, org, _ = _setup(connector)
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.status == "completed"
    assert run.transactions_created == 6
    assert db.query(BankTransaction).count() == 6


def test_repeated_pagination_cursor_fails_cleanly():
    txs = [
        make_tx("fake-acc-1", date(2026, 7, d), f"OP {d}", -1.0, external_id=f"c-{d}")
        for d in range(1, 5)
    ]
    connector = FakeBankConnector(
        transactions={"fake-acc-1": txs}, page_size=2, repeat_cursor=True
    )
    db, org, _ = _setup(connector)
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.status == "failed"
    assert "curseur répété" in (run.error_message or "")


def test_retry_after_pagination_interrupt_creates_no_duplicates():
    txs = [
        make_tx("fake-acc-1", date(2026, 7, d), f"OP {d}", -1.0, external_id=f"r-{d}")
        for d in range(1, 5)
    ]
    connector = FakeBankConnector(
        transactions={"fake-acc-1": txs}, page_size=2, fail_on_page=2, fail_retryable=True
    )
    db, org, _ = _setup(connector)
    engine = SyncEngine(db, max_attempts=1)
    failed = engine.run_sync(org.id)[0]
    assert failed.status == "failed"
    created_after_fail = db.query(BankTransaction).count()
    assert created_after_fail == 2

    connector.fail_on_page = None
    resumed = SyncEngine(db, max_attempts=1).run_sync(org.id)[0]
    assert resumed.status == "completed"
    assert db.query(BankTransaction).count() == 4
    ids = [r.external_id for r in db.query(BankTransaction).all()]
    assert len(ids) == len(set(ids))


def test_missing_external_id_does_not_drop_second_movement():
    a = make_tx("fake-acc-1", date(2026, 7, 1), "RESTAURANT", -25.0, external_id="")
    b = make_tx("fake-acc-1", date(2026, 7, 1), "RESTAURANT", -25.0, external_id="")
    connector = FakeBankConnector(transactions={"fake-acc-1": [a, b]})
    db, org, _ = _setup(connector)
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.transactions_created == 2
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    assert all(r.external_id == "" for r in rows)
    assert sum(1 for r in rows if r.is_duplicate) == 1


def test_overlap_window_captures_past_transaction_update():
    original = make_tx("fake-acc-1", date(2026, 7, 1), "LOYER", -900.0, external_id="past-1")
    connector = FakeBankConnector(transactions={"fake-acc-1": [original]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    connector.transactions["fake-acc-1"] = [
        original.model_copy(update={"label": "LOYER CORRIGE"})
    ]
    run = engine.run_sync(org.id)[0]
    assert run.sync_type == "incremental"
    assert run.transactions_updated == 1
    assert db.query(BankTransaction).one().label == "LOYER CORRIGE"


def test_sync_does_not_purge_missing_provider_rows():
    connector = FakeBankConnector(transactions={"fake-acc-1": list(BASE_TXS)})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    connector.transactions["fake-acc-1"] = [BASE_TXS[0]]
    engine.run_sync(org.id)
    assert db.query(BankTransaction).count() == 3
