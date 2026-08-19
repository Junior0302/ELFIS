"""Tests API /banking/* — cohérence des endpoints REST."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.banking.api.routes import admin_router, router
from app.banking.connectors import registry
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import User

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_db,
    make_tx,
    seed_org,
)


@pytest.fixture()
def client_ctx():
    db = make_banking_db()
    org = seed_org(db)
    user = User(
        email="owner@test.local",
        first_name="Owner",
        last_name="Test",
        status="active",
        password_hash="x",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT CLIENT ALPHA", 500.0),
                make_tx("fake-acc-1", date(2026, 7, 3), "LOYER BUREAUX", -900.0),
            ]
        }
    )
    registry.register_connector("fake", lambda: connector)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(admin_router, prefix="/api")

    def _auth():
        return AuthContext(
            user=user, organization_id=org.id, role="owner", permissions=["*"]
        )

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = _auth
    client = TestClient(app)
    headers = {"X-Organization-Id": str(org.id)}
    yield client, headers, db, org, connector
    registry.unregister_connector("fake")
    db.close()


def test_connectors_endpoint_lists_providers_and_connections(client_ctx):
    client, headers, *_ = client_ctx
    res = client.get("/api/banking/connectors", headers=headers)
    assert res.status_code == 200
    data = res.json()
    providers = {p["provider"] for p in data["providers"]}
    assert {"demo", "bridge", "powens", "fake"}.issubset(providers)
    assert data["connections"] == []


def test_full_api_flow_connect_sync_accounts_transactions_status_health(client_ctx):
    client, headers, db, org, connector = client_ctx

    # Connexion
    res = client.post(
        "/api/banking/connectors/connect",
        json={"provider": "fake", "bank_name": "Banque Factice"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    connection_id = body["connection"]["id"]
    assert body["connection"]["status"] == "connected"
    assert len(body["accounts"]) == 1

    # Synchronisation
    res = client.post("/api/banking/sync", json={}, headers=headers)
    assert res.status_code == 200
    sync_body = res.json()
    assert sync_body["ok"] is True
    assert sync_body["runs"][0]["transactions_created"] == 2

    # Comptes
    res = client.get("/api/banking/accounts", headers=headers)
    assert res.status_code == 200
    accounts = res.json()
    assert accounts["total"] == 1
    assert accounts["items"][0]["provider"] == "fake"

    # Transactions normalisées + filtres
    res = client.get("/api/banking/transactions", headers=headers)
    assert res.status_code == 200
    txs = res.json()
    assert txs["total"] == 2
    first = txs["items"][0]
    for field in (
        "external_id",
        "booked_at",
        "label",
        "amount",
        "currency",
        "account_id",
        "category",
        "status",
        "source",
    ):
        assert field in first
    res = client.get("/api/banking/transactions?q=loyer", headers=headers)
    assert res.json()["total"] == 1

    # Journal de synchronisation
    res = client.get("/api/banking/sync", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] == 1

    # Statut global
    res = client.get("/api/banking/status", headers=headers)
    assert res.status_code == 200
    status = res.json()
    assert status["connections_connected"] == 1
    assert status["transactions_total"] == 2

    # Santé
    res = client.get("/api/banking/health", headers=headers)
    assert res.status_code == 200
    health = res.json()
    assert health["connections"][0]["connection_id"] == connection_id
    assert health["connections"][0]["failure_rate"] == 0.0
    assert health["summary"]["runs_total"] == 1

    # Déconnexion
    res = client.post(
        f"/api/banking/connectors/{connection_id}/disconnect", headers=headers
    )
    assert res.status_code == 200
    assert res.json()["connection"]["status"] == "disconnected"

    # Sync refusée après déconnexion
    res = client.post("/api/banking/sync", json={}, headers=headers)
    assert res.status_code == 400


def test_connect_unknown_provider_returns_400(client_ctx):
    client, headers, *_ = client_ctx
    res = client.post(
        "/api/banking/connectors/connect",
        json={"provider": "inconnu", "bank_name": "X"},
        headers=headers,
    )
    assert res.status_code == 400


def test_platform_admin_overview_requires_admin(client_ctx):
    client, headers, *_ = client_ctx
    res = client.get("/api/platform/banking/overview", headers=headers)
    assert res.status_code == 401
