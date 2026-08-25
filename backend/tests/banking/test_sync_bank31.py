"""BANK-3.1 — contrainte unique, verrou, upsert atomique, événements."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.banking.api.routes import _raise_domain
from app.banking.banking_types import TransactionStatus
from app.banking.connectors import registry
from app.banking.engine import BankingEngine, SyncAlreadyInProgressError
from app.banking.sync_engine import SyncEngine
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models import BankAccount, BankTransaction

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


def _tx_row(**kwargs) -> BankTransaction:
    payload = {
        "account_id": 1,
        "external_id": "ext-1",
        "booked_at": "2026-07-01",
        "label": "VIREMENT",
        "amount": 10.0,
        "currency": "EUR",
        "category": "autre",
        "status": "booked",
        "source": "fake",
    }
    payload.update(kwargs)
    return BankTransaction(**payload)


def _created_events(db):
    return (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_CREATED)
        .all()
    )


def _updated_events(db):
    return (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_TRANSACTION_UPDATED)
        .all()
    )


def test_unique_index_same_account_same_external_id_one_row():
    db = make_banking_db()
    db.add(_tx_row(account_id=41, external_id="same-ext"))
    db.commit()
    db.add(_tx_row(account_id=41, external_id="same-ext", label="AUTRE"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.query(BankTransaction).filter(BankTransaction.account_id == 41).count() == 1


def test_unique_index_allows_same_external_id_on_different_accounts():
    db = make_banking_db()
    db.add(_tx_row(account_id=51, external_id="shared-ext"))
    db.add(_tx_row(account_id=52, external_id="shared-ext"))
    db.commit()
    assert db.query(BankTransaction).filter(BankTransaction.external_id == "shared-ext").count() == 2


def test_empty_external_id_keeps_two_observations():
    a = make_tx("fake-acc-1", date(2026, 7, 1), "RESTAURANT", -25.0, external_id="")
    b = make_tx("fake-acc-1", date(2026, 7, 1), "RESTAURANT", -25.0, external_id="")
    connector = FakeBankConnector(transactions={"fake-acc-1": [a, b]})
    db, org, _ = _setup(connector)
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.transactions_created == 2
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    assert all(r.external_id == "" for r in rows)


def test_second_sync_unchanged_emits_no_created_event():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "LOYER", -900.0, external_id="rent-1")
            ]
        }
    )
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    first = engine.run_sync(org.id)[0]
    assert first.transactions_created == 1
    assert len(_created_events(db)) == 1
    second = engine.run_sync(org.id)[0]
    assert second.transactions_created == 0
    assert second.transactions_updated == 0
    assert db.query(BankTransaction).count() == 1
    assert len(_created_events(db)) == 1
    assert _updated_events(db) == []


def test_second_sync_with_change_updates_same_row_and_emits_updated():
    original = make_tx("fake-acc-1", date(2026, 7, 1), "LOYER", -900.0, external_id="rent-2")
    connector = FakeBankConnector(transactions={"fake-acc-1": [original]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    connector.transactions["fake-acc-1"] = [
        original.model_copy(update={"label": "LOYER CORRIGE"})
    ]
    run = engine.run_sync(org.id)[0]
    assert run.transactions_updated == 1
    assert db.query(BankTransaction).count() == 1
    assert db.query(BankTransaction).one().label == "LOYER CORRIGE"
    assert len(_created_events(db)) == 1
    assert len(_updated_events(db)) == 1


def test_pending_to_booked_same_external_id_one_row():
    pending = make_tx(
        "fake-acc-1",
        date(2026, 7, 1),
        "PAIEMENT CARTE",
        -25.0,
        status=TransactionStatus.pending,
        external_id="card-bank31",
    )
    connector = FakeBankConnector(transactions={"fake-acc-1": [pending]})
    db, org, _ = _setup(connector)
    engine = SyncEngine(db)
    engine.run_sync(org.id)
    connector.transactions["fake-acc-1"] = [
        pending.model_copy(update={"status": TransactionStatus.booked})
    ]
    run = engine.run_sync(org.id)[0]
    assert run.transactions_created == 0
    assert run.transactions_updated == 1
    row = db.query(BankTransaction).one()
    assert row.status == "booked"
    assert row.external_id == "card-bank31"
    assert len(_created_events(db)) == 1
    assert len(_updated_events(db)) == 1


def test_different_external_ids_remain_two_transactions():
    a = make_tx("fake-acc-1", date(2026, 7, 1), "RESTAURANT", -25.0, external_id="id-a")
    b = make_tx("fake-acc-1", date(2026, 7, 1), "RESTAURANT", -25.0, external_id="id-b")
    connector = FakeBankConnector(transactions={"fake-acc-1": [a, b]})
    db, org, _ = _setup(connector)
    SyncEngine(db).run_sync(org.id)
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    assert {r.external_id for r in rows} == {"id-a", "id-b"}


def test_same_external_id_two_organizations_no_cross_conflict():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "X", 10.0, external_id="tenant-ext")
            ]
        }
    )
    db = make_banking_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    _register(connector)
    BankingEngine(db).connect(organization_id=org_a.id, provider="fake", bank_name="A")
    BankingEngine(db).connect(organization_id=org_b.id, provider="fake", bank_name="B")
    SyncEngine(db).run_sync(org_a.id)
    SyncEngine(db).run_sync(org_b.id)
    rows = db.query(BankTransaction).all()
    assert len(rows) == 2
    account_orgs = {
        db.query(BankAccount).filter(BankAccount.id == r.account_id).one().organization_id
        for r in rows
    }
    assert account_orgs == {org_a.id, org_b.id}


def test_created_event_payload_has_no_secrets():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT", 12.0, external_id="evt-1")
            ]
        }
    )
    db, org, _ = _setup(connector)
    SyncEngine(db).run_sync(org.id)
    payload = _created_events(db)[0].payload
    blob = str(payload).lower()
    assert "iban" not in blob
    assert "token" not in blob
    assert "client_secret" not in blob
    assert "password" not in blob
    assert payload["transaction_id"]
    assert payload["external_id"] == "evt-1"


def test_sync_already_in_progress_maps_to_http_409():
    with pytest.raises(HTTPException) as caught:
        _raise_domain(SyncAlreadyInProgressError("Une synchronisation est déjà en cours"))
    assert caught.value.status_code == 409


def test_sqlite_sync_lock_rejects_second_acquire_until_release():
    from app.banking.sync_lock import (
        acquire_connection_sync_lock,
        release_connection_sync_lock,
    )

    db = make_banking_db()
    held = acquire_connection_sync_lock(
        db, organization_id=1, connection_id=77, wait_seconds=0
    )
    assert held is not None
    assert (
        acquire_connection_sync_lock(
            db, organization_id=1, connection_id=77, wait_seconds=0
        )
        is None
    )
    release_connection_sync_lock(held)
    held_again = acquire_connection_sync_lock(
        db, organization_id=1, connection_id=77, wait_seconds=0
    )
    assert held_again is not None
    release_connection_sync_lock(held_again)


def test_sync_already_in_progress_when_connection_lock_held():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "CONC", 1.0, external_id="conc-lock")
            ]
        }
    )
    db, org, connection = _setup(connector)
    from app.banking.sync_lock import (
        acquire_connection_sync_lock,
        release_connection_sync_lock,
    )

    held = acquire_connection_sync_lock(
        db,
        organization_id=org.id,
        connection_id=connection.id,
        wait_seconds=0,
    )
    assert held is not None
    try:
        with pytest.raises(SyncAlreadyInProgressError):
            SyncEngine(db, lock_wait_seconds=0).run_sync(org.id)
    finally:
        release_connection_sync_lock(held)

    run = SyncEngine(db, lock_wait_seconds=0).run_sync(org.id)[0]
    assert run.status == "completed"
    assert db.query(BankTransaction).count() == 1
    assert len(_created_events(db)) == 1


def test_provider_external_id_whitespace_is_stripped_not_merged_heuristically():
    padded = make_tx(
        "fake-acc-1", date(2026, 7, 1), "VIREMENT", 10.0, external_id="  ext-pad-1  "
    )
    assert padded.external_id == "ext-pad-1"
    connector = FakeBankConnector(transactions={"fake-acc-1": [padded]})
    db, org, _ = _setup(connector)
    SyncEngine(db).run_sync(org.id)
    assert db.query(BankTransaction).one().external_id == "ext-pad-1"

    connector.transactions["fake-acc-1"] = [
        make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT", 10.0, external_id="ext-pad-1")
    ]
    run = SyncEngine(db).run_sync(org.id)[0]
    assert run.transactions_created == 0
    assert db.query(BankTransaction).count() == 1
