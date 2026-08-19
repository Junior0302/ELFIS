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


def test_fingerprint_duplicate_skipped_even_with_different_external_id():
    duplicate = make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT CLIENT ALPHA", 500.0)
    duplicate = duplicate.model_copy(update={"external_id": "autre-id-fournisseur"})
    connector = FakeBankConnector(
        transactions={"fake-acc-1": [BASE_TXS[0], duplicate]}
    )
    db, org, _ = _setup(connector)
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.transactions_created == 1
    assert run.duplicates_skipped == 1
    assert db.query(BankTransaction).count() == 1


def test_transaction_update_publishes_updated_event():
    connector = FakeBankConnector(transactions={"fake-acc-1": [BASE_TXS[0]]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)

    # Le fournisseur corrige le libellé de la même transaction (même external_id)
    corrected = BASE_TXS[0].model_copy(update={"label": "VIREMENT CLIENT ALPHA CORRIGE"})
    connector.transactions["fake-acc-1"] = [corrected]
    # resync complet (curseur au 2026-07-01, la tx n'est pas > curseur → on la repousse)
    connector.transactions["fake-acc-1"] = [
        corrected.model_copy(update={"booked_at": date(2026, 7, 2)})
    ]
    run = engine.run_sync(org.id)[0]
    # Nouvelle date → nouvel enregistrement n'est PAS créé car même external_id : update
    assert run.transactions_updated == 1
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
