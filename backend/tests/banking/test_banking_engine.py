"""Tests Banking Engine — source de vérité, connexion et déconnexion."""

from __future__ import annotations

from datetime import date

import pytest

from app.banking.connectors import registry
from app.banking.engine import BankingEngine, BankingEngineError
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models import BankAccount

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_db,
    make_tx,
    seed_org,
)


@pytest.fixture()
def fake_connector():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT CLIENT ALPHA", 500.0),
            ]
        }
    )
    registry.register_connector("fake", lambda: connector)
    yield connector
    registry.unregister_connector("fake")


def test_connect_creates_connection_and_imports_accounts(fake_connector):
    db = make_banking_db()
    org = seed_org(db)
    engine = BankingEngine(db)

    connection = engine.connect(
        organization_id=org.id, provider="fake", bank_name="Banque Factice"
    )
    assert connection.status == "connected"
    assert connection.provider == "fake"
    assert fake_connector.connect_calls == 1

    accounts = engine.list_accounts(org.id)
    assert len(accounts) == 1
    account = accounts[0]
    assert account.connection_id == connection.id
    assert account.provider == "fake"
    assert account.external_id == "fake-acc-1"
    assert account.iban.startswith("FR")
    assert account.balance == 1000.0
    assert account.connected is True

    event = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_CONNECTION_CONNECTED)
        .first()
    )
    assert event is not None
    assert event.organization_id == org.id


def test_connect_is_idempotent_per_provider_connection(fake_connector):
    db = make_banking_db()
    org = seed_org(db)
    engine = BankingEngine(db)
    c1 = engine.connect(organization_id=org.id, provider="fake", bank_name="A")
    c2 = engine.connect(organization_id=org.id, provider="fake", bank_name="A")
    assert c1.id == c2.id
    assert len(engine.list_connections(org.id)) == 1
    assert len(engine.list_accounts(org.id)) == 1  # pas de compte dupliqué


def test_disconnect_marks_connection_and_accounts(fake_connector):
    db = make_banking_db()
    org = seed_org(db)
    engine = BankingEngine(db)
    connection = engine.connect(organization_id=org.id, provider="fake", bank_name="A")

    disconnected = engine.disconnect(organization_id=org.id, connection_id=connection.id)
    assert disconnected.status == "disconnected"
    assert fake_connector.disconnect_calls == 1
    account = db.query(BankAccount).filter(BankAccount.connection_id == connection.id).one()
    assert account.connected is False

    event = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.BANKING_CONNECTION_DISCONNECTED)
        .first()
    )
    assert event is not None


def test_disconnect_unknown_connection_raises(fake_connector):
    db = make_banking_db()
    org = seed_org(db)
    with pytest.raises(BankingEngineError):
        BankingEngine(db).disconnect(organization_id=org.id, connection_id=999)


def test_org_isolation(fake_connector):
    db = make_banking_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    engine = BankingEngine(db)
    connection = engine.connect(organization_id=org_a.id, provider="fake", bank_name="A")

    assert engine.list_connections(org_b.id) == []
    assert engine.list_accounts(org_b.id) == []
    with pytest.raises(BankingEngineError):
        engine.get_connection(org_b.id, connection.id)


def test_status_aggregates_source_of_truth(fake_connector):
    db = make_banking_db()
    org = seed_org(db)
    engine = BankingEngine(db)
    engine.connect(organization_id=org.id, provider="fake", bank_name="A")
    status = engine.status(org.id)
    assert status["connections_total"] == 1
    assert status["connections_connected"] == 1
    assert status["accounts_total"] == 1
    assert status["balances_by_currency"] == {"EUR": 1000.0}
