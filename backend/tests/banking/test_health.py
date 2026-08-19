"""Tests Banking Health — métriques org et vue Cockpit Admin."""

from __future__ import annotations

from datetime import date

import pytest

from app.banking.connectors import registry
from app.banking.engine import BankingEngine
from app.banking.health import BankingHealthService
from app.banking.sync_engine import SyncEngine

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_db,
    make_tx,
    seed_org,
)


@pytest.fixture(autouse=True)
def _cleanup_registry():
    yield
    registry.unregister_connector("fake")


def test_health_reports_syncs_errors_and_average_duration():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT", 100.0)]
        }
    )
    registry.register_connector("fake", lambda: connector)
    db = make_banking_db()
    org = seed_org(db)
    BankingEngine(db).connect(organization_id=org.id, provider="fake", bank_name="A")
    engine = SyncEngine(db, max_attempts=1)
    engine.run_sync(org.id)  # succès
    connector.fail_times = 1
    engine.run_sync(org.id)  # échec

    health = BankingHealthService(db).organization_health(org.id)
    item = health["connections"][0]
    assert item["runs_total"] == 2
    assert item["runs_failed"] == 1
    assert item["failure_rate"] == 0.5
    assert item["avg_duration_ms"] is not None
    assert item["last_sync_at"] is not None
    assert item["provider_health"]["provider"] == "fake"
    providers = {p["provider"] for p in health["providers"]}
    assert {"demo", "bridge", "powens"}.issubset(providers)


def test_platform_overview_aggregates_all_organizations():
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT", 100.0)]
        }
    )
    registry.register_connector("fake", lambda: connector)
    db = make_banking_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    engine = BankingEngine(db)
    engine.connect(organization_id=org_a.id, provider="fake", bank_name="A")
    engine.connect(organization_id=org_b.id, provider="fake", bank_name="B")
    sync = SyncEngine(db, max_attempts=1)
    sync.run_sync(org_a.id)
    connector.fail_times = 1
    sync.run_sync(org_b.id)

    overview = BankingHealthService(db).platform_overview()
    assert overview["connections_total"] == 2
    assert overview["connections_active"] == 1
    assert overview["connections_error"] == 1
    assert overview["runs_total"] == 2
    assert overview["runs_failed"] == 1
    assert overview["failure_rate"] == 0.5
    assert overview["recent_errors"]
    assert overview["by_provider"][0]["provider"] == "fake"
