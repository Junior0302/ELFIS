"""Legacy /dashboard/stats et /dashboard/pilot — encore actifs mais deprecated."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import User
from app.routers import dashboard as dashboard_router

from tests.financial.helpers import make_financial_db, seed_finance_data, seed_org


@pytest.fixture()
def legacy_client():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)
    user = User(
        email="legacy@test.local",
        first_name="Legacy",
        last_name="Test",
        status="active",
        password_hash="x",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    app = FastAPI()
    app.include_router(dashboard_router.router, prefix="/api")

    def _auth():
        return AuthContext(user=user, organization_id=org.id, role="owner", permissions=["*"])

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = _auth
    client = TestClient(app)
    yield client, org
    db.close()


def test_legacy_stats_still_responds_with_deprecation_headers(legacy_client):
    client, _ = legacy_client
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"
    assert "financial/overview" in (res.headers.get("Link") or "")
    body = res.json()
    assert "invoice_count" in body
    assert "total_ht" in body


def test_legacy_pilot_still_responds_with_deprecation_headers(legacy_client):
    client, _ = legacy_client
    res = client.get("/api/dashboard/pilot")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"
    data = res.json()
    # Structure pilot legacy (pas le schéma Financial Engine)
    assert "tresorerie" in data or "ca" in data or "health" in data
