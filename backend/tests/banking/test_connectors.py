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
    "health",
]


def test_all_providers_implement_the_common_interface():
    for provider in ("demo", "bridge", "powens"):
        connector = registry.get_connector(provider)
        assert isinstance(connector, BankConnector)
        for method in REQUIRED_METHODS:
            assert callable(getattr(connector, method)), f"{provider}.{method} manquant"


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
