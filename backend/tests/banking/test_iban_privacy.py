"""BANK-2 — masquage IBAN, API sûre, Event Bus, soldes, isolation tenant."""

from __future__ import annotations

import logging
from datetime import date

from app.banking.account_types import normalize_account_type
from app.banking.banking_types import NormalizedAccount
from app.banking.connectors import registry
from app.banking.engine import BankingEngine
from app.banking.iban import iban_last4, mask_iban
from app.banking.sync_engine import SyncEngine
from app.events.event_models import ElfisEvent
from app.models import BankAccount

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_db,
    make_tx,
    seed_org,
)


DEMO_IBAN = "FR7630001007941234567890185"
FAKE_IBAN = "FR7699999000011234567890147"


def test_mask_iban_french():
    masked = mask_iban(DEMO_IBAN)
    assert masked.startswith("FR76")
    assert masked.endswith("0185")
    assert "••••" in masked
    assert "30001007941234567890" not in masked.replace(" ", "")
    assert iban_last4(DEMO_IBAN) == "0185"


def test_mask_iban_foreign():
    masked = mask_iban("DE89370400440532013000")
    assert masked.startswith("DE89")
    assert masked.endswith("3000")
    assert "370400440532" not in masked.replace(" ", "")


def test_mask_iban_with_spaces():
    assert mask_iban("FR76 3000 1007 9412 3456 7890 185") == mask_iban(DEMO_IBAN)


def test_mask_iban_short_invalid_and_none():
    assert mask_iban(None) == ""
    assert mask_iban("") == ""
    assert mask_iban("   ") == ""
    assert mask_iban("FR") == "••••"
    assert mask_iban("FR76") == "•••• FR76"
    assert mask_iban("1234567") == "•••• 4567"
    assert iban_last4(None) is None
    assert iban_last4("AB") is None


def test_unknown_account_type_becomes_other():
    assert normalize_account_type("life_insurance") == "investment"
    assert normalize_account_type("n'importe-quoi") == "other"
    assert normalize_account_type(None) == "other"
    assert normalize_account_type(42) == "other"


def test_available_balance_none_stays_null():
    acc = NormalizedAccount(
        external_id="a1",
        label="Compte",
        balance=10.0,
        available_balance=None,
        account_type="checking",
    )
    assert acc.available_balance is None


def test_api_and_events_never_contain_full_iban():
    db = make_banking_db()
    org = seed_org(db)
    connector = FakeBankConnector()
    registry.register_connector("fake", lambda: connector)
    try:
        engine = BankingEngine(db)
        connection = engine.connect(organization_id=org.id, provider="fake", bank_name="A")
        SyncEngine(db).run_sync(org.id, connection_id=connection.id)
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.banking.api.routes import router
        from app.database import get_db
        from app.deps import AuthContext, get_auth_context, require_active_subscription
        from app.models_saas import User

        user = User(
            email="a@test.local",
            first_name="A",
            last_name="O",
            status="active",
            password_hash="x",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        app = FastAPI()
        app.include_router(router, prefix="/api")

        def _auth():
            return AuthContext(
                user=user, organization_id=org.id, role="owner", permissions=["*"]
            )

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_auth_context] = _auth
        app.dependency_overrides[require_active_subscription] = _auth
        client = TestClient(app)
        res = client.get("/api/banking/accounts", headers={"X-Organization-Id": str(org.id)})
        assert res.status_code == 200
        blob = res.text
        assert FAKE_IBAN not in blob
        assert DEMO_IBAN not in blob
        item = res.json()["items"][0]
        assert "iban" not in item
        assert item["iban_masked"]
        assert "••••" in item["iban_masked"]
        assert item["iban_last4"] == "0147"
        assert item["available_balance"] is None
        assert item["account_type"] == "checking"
        txs = client.get("/api/banking/transactions", headers={"X-Organization-Id": str(org.id)})
        assert txs.status_code == 200
        assert FAKE_IBAN not in txs.text
        assert all("iban" not in item for item in txs.json()["items"])

        events = db.query(ElfisEvent).filter(ElfisEvent.event_name.like("banking.%")).all()
        assert events
        for event in events:
            payload = event.payload or {}
            dumped = str(payload)
            assert FAKE_IBAN not in dumped
            assert "iban" not in payload
    finally:
        registry.unregister_connector("fake")
        db.close()


def test_org_a_cannot_read_org_b_accounts():
    db = make_banking_db()
    org_a = seed_org(db, "Org A")
    org_b = seed_org(db, "Org B")
    connector = FakeBankConnector()
    registry.register_connector("fake", lambda: connector)
    try:
        engine = BankingEngine(db)
        engine.connect(organization_id=org_a.id, provider="fake", bank_name="A")
        assert engine.list_accounts(org_b.id) == []
        assert engine.list_accounts(org_a.id)
        assert all(a.organization_id == org_a.id for a in engine.list_accounts(org_a.id))
        foreign = (
            db.query(BankAccount)
            .filter(BankAccount.organization_id == org_b.id)
            .all()
        )
        assert foreign == []
    finally:
        registry.unregister_connector("fake")
        db.close()


def test_mixed_currencies_are_not_summed_in_banking_status():
    db = make_banking_db()
    org = seed_org(db)
    db.add(
        BankAccount(
            organization_id=org.id,
            provider="fake",
            label="EUR",
            currency="EUR",
            balance=100.0,
            connected=True,
        )
    )
    db.add(
        BankAccount(
            organization_id=org.id,
            provider="fake",
            label="USD",
            currency="USD",
            balance=200.0,
            connected=True,
        )
    )
    db.commit()
    status = BankingEngine(db).status(org.id)
    assert status["balances_by_currency"] == {"EUR": 100.0, "USD": 200.0}
    assert 300.0 not in status["balances_by_currency"].values()


def test_bank2_logs_never_contain_full_iban(caplog):
    db = make_banking_db()
    org = seed_org(db)
    connector = FakeBankConnector()
    registry.register_connector("fake", lambda: connector)
    try:
        with caplog.at_level(logging.DEBUG):
            BankingEngine(db).connect(organization_id=org.id, provider="fake", bank_name="A")
        assert FAKE_IBAN not in caplog.text
        assert DEMO_IBAN not in caplog.text
    finally:
        registry.unregister_connector("fake")
        db.close()


def test_sync_engine_keeps_available_balance_null():
    db = make_banking_db()
    org = seed_org(db)
    connector = FakeBankConnector(
        transactions={"fake-acc-1": [make_tx("fake-acc-1", date(2026, 8, 1), "TEST", 10.0)]}
    )
    registry.register_connector("fake", lambda: connector)
    try:
        engine = BankingEngine(db)
        connection = engine.connect(organization_id=org.id, provider="fake", bank_name="A")
        SyncEngine(db).run_sync(org.id, connection_id=connection.id)
        account = engine.list_accounts(org.id)[0]
        assert account.available_balance is None
    finally:
        registry.unregister_connector("fake")
        db.close()
