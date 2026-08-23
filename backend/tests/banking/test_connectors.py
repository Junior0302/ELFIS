"""Tests Connector Layer — interface commune et interchangeabilité des fournisseurs."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.banking.banking_types import NormalizedAccount, NormalizedTransaction
from app.banking.connectors import registry
from app.banking.connectors.base import BankConnector, ConnectorError
from app.banking.connectors.bridge import BridgeBankConnector
from app.banking.connectors.demo import DemoBankConnector
from app.banking.connectors.powens import PowensBankConnector


REQUIRED_METHODS = [
    "connect",
    "disconnect",
    "refresh",
    "list_accounts",
    "list_transactions",
    "list_transaction_page",
    "health",
]


def test_all_providers_implement_the_common_interface():
    for provider in ("demo", "bridge", "powens"):
        connector = registry.get_connector(provider)
        assert isinstance(connector, BankConnector)
        for method in REQUIRED_METHODS:
            assert callable(getattr(connector, method)), f"{provider}.{method} manquant"
    assert registry.get_connector("bridge").requires_user_consent is True
    assert registry.get_connector("demo").requires_user_consent is False
    assert registry.get_connector("powens").requires_user_consent is False


def test_registry_lists_and_resolves_providers():
    providers = registry.list_providers()
    assert {"demo", "bridge", "powens"}.issubset(set(providers))
    assert isinstance(registry.get_connector("demo"), DemoBankConnector)
    assert isinstance(registry.get_connector("bridge"), BridgeBankConnector)
    assert isinstance(registry.get_connector("powens"), PowensBankConnector)


def test_unknown_provider_rejected():
    with pytest.raises(ConnectorError):
        registry.get_connector("nexiste-pas")


def test_unconfigured_providers_report_not_configured_health():
    for provider in ("bridge", "powens"):
        connector = registry.get_connector(provider)
        health = connector.health()
        assert health.provider == provider
        # Sans identifiants API en environnement de test
        if not getattr(connector, "configured", False):
            assert health.status == "not_configured"
            assert health.configured is False


def test_unconfigured_provider_refuses_connect():
    connector = PowensBankConnector()
    if connector.configured:
        pytest.skip("Powens configuré dans cet environnement")
    with pytest.raises(ConnectorError):
        connector.connect(organization_id=1, bank_name="Test")


def test_bridge_refuses_direct_connect_and_unconfigured_consent():
    connector = BridgeBankConnector()
    with pytest.raises(ConnectorError, match="consentement"):
        connector.connect(organization_id=1, bank_name="Test")
    if connector.configured:
        pytest.skip("Bridge configuré dans cet environnement")
    with pytest.raises(ConnectorError):
        connector.start_user_consent(
            organization_id=1,
            callback_url="http://localhost/callback",
        )


def test_demo_connector_full_lifecycle_and_normalization():
    connector = DemoBankConnector()
    connection_id = connector.connect(organization_id=42, bank_name="Ma banque")
    assert connection_id == "demo-conn-42"

    accounts = connector.list_accounts(connection_id)
    assert accounts and isinstance(accounts[0], NormalizedAccount)
    account = accounts[0]
    assert account.currency == "EUR"
    assert account.iban.startswith("FR")

    transactions = connector.list_transactions(connection_id, account.external_id)
    assert transactions
    for tx in transactions:
        assert isinstance(tx, NormalizedTransaction)
        assert tx.external_id
        assert tx.account_external_id == account.external_id
        assert tx.source == "demo"
        assert tx.currency == "EUR"
        assert tx.status.value in ("booked", "pending")
        assert isinstance(tx.booked_at, date)

    # Déconnexion / refresh ne lèvent pas
    connector.refresh(connection_id)
    connector.disconnect(connection_id)
    assert connector.health().status == "ok"


def test_demo_connector_supports_incremental_since():
    connector = DemoBankConnector()
    connection_id = connector.connect(organization_id=1, bank_name="X")
    account = connector.list_accounts(connection_id)[0]
    full = connector.list_transactions(connection_id, account.external_id)
    cutoff = date.today() - timedelta(days=15)
    partial = connector.list_transactions(connection_id, account.external_id, since=cutoff)
    assert len(partial) < len(full)
    assert all(t.booked_at > cutoff for t in partial)
    restaurants = [t for t in full if t.label == "RESTAURANT"]
    assert len(restaurants) == 2
    assert restaurants[0].external_id != restaurants[1].external_id
    pages = []
    cursor = None
    while True:
        page = connector.list_transaction_page(
            connection_id, account.external_id, cursor=cursor
        )
        pages.append(page)
        if not page.has_more:
            break
        cursor = page.next_cursor
    assert len(pages) >= 2
    assert sum(len(p.transactions) for p in pages) == len(full)
    pending = [t for t in full if t.status.value == "pending"]
    assert pending and pending[0].external_id == "demo-tx-card-pending"
    incremental = connector.list_transactions(connection_id, account.external_id, since=cutoff)
    booked_card = [t for t in incremental if t.external_id == "demo-tx-card-pending"]
    assert booked_card and booked_card[0].status.value == "booked"


def test_bridge_and_powens_ignore_unknown_fields():
    from app.banking.connectors.bridge import map_bridge_transaction
    from app.banking.connectors.powens import map_powens_transaction

    mapped = map_bridge_transaction(
        {
            "id": "br-1",
            "booking_date": "2026-07-01",
            "value_date": "2026-07-02",
            "clean_description": "Cafe",
            "amount": -12.5,
            "currency_code": "EUR",
            "future": False,
            "unknown_blob": {"secret": "nope"},
            "iban": "FR7611111111111111111111111",
            "counterparty": {"name": "Cafe Dupont", "iban": "FR762222"},
            "reference": "END2END",
        },
        "acc-1",
    )
    assert mapped is not None
    assert mapped.external_id == "br-1"
    assert mapped.value_date.isoformat() == "2026-07-02"
    assert mapped.counterparty_name == "Cafe Dupont"
    assert mapped.reference == "END2END"
    assert "iban" not in mapped.model_dump()

    powens = map_powens_transaction(
        {
            "id": 99,
            "date": "2026-07-03",
            "rdate": "2026-07-04",
            "simplified_wording": "Loyer",
            "wording": "SCI PARIS",
            "value": -900,
            "currency": {"id": "EUR"},
            "coming": True,
            "weird": True,
            "iban": "FR763333",
        },
        "acc-2",
    )
    assert powens is not None
    assert powens.external_id == "99"
    assert powens.status.value == "pending"
    assert powens.counterparty_name == "SCI PARIS"
    assert "iban" not in powens.model_dump()


def test_normalized_transaction_validation():
    with pytest.raises(Exception):
        NormalizedTransaction(
            external_id="x",
            booked_at=date.today(),
            label="   ",  # libellé vide interdit
            amount=1.0,
            account_external_id="a",
            source="demo",
        )
