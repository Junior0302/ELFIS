"""Tests API /financial/* — cohérence des endpoints REST."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.deps import (
    AuthContext,
    get_auth_context,
    require_active_subscription,
    require_platform_admin,
)
from app.financial.api.routes import admin_router, router
from app.models_saas import User

from tests.financial.helpers import make_financial_db, seed_finance_data, seed_org


@pytest.fixture()
def client_ctx():
    db = make_financial_db()
    org = seed_org(db)
    seed_finance_data(db, org.id)
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

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(admin_router, prefix="/api")

    def _auth():
        return AuthContext(user=user, organization_id=org.id, role="owner", permissions=["*"])

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = _auth
    app.dependency_overrides[require_platform_admin] = _auth
    client = TestClient(app)
    yield client, db, org
    db.close()


def test_overview_endpoint_returns_full_dashboard(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/financial/overview")
    assert res.status_code == 200
    data = res.json()
    assert set(data.keys()) >= {
        "kpis", "alerts", "health", "charts", "trends", "sync",
        "recent_activity", "documents_to_process", "has_data", "recommendations",
    }
    assert len(data["kpis"]) == 9
    assert data["has_data"] is True
    assert data["health"]["state"] == "active"
    assert len(data["recent_activity"]) > 0


def test_kpis_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/financial/kpis")
    assert res.status_code == 200
    kpis = res.json()["kpis"]
    assert [k["id"] for k in kpis][:2] == ["tresorerie", "revenus"]
    tresorerie = kpis[0]
    assert tresorerie["value"] == 12000.0
    assert tresorerie["unit"] == "EUR"


def test_trends_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/financial/trends")
    assert res.status_code == 200
    data = res.json()
    assert set(data.keys()) == {"monthly", "weekly", "yearly"}
    assert "comparison" in data["monthly"]


def test_charts_endpoint_provides_all_series(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/financial/charts")
    assert res.status_code == 200
    data = res.json()
    assert set(data.keys()) == {
        "revenue_vs_expenses", "treasury", "expense_breakdown", "categories", "ca_evolution",
    }
    assert data["treasury"][-1]["value"] == 12000.0
    breakdown = data["expense_breakdown"]
    assert breakdown[0]["category"] == "loyer"
    assert breakdown[0]["amount"] == 3500.0
    assert abs(sum(b["pct"] for b in breakdown) - 100.0) < 1.0


def test_alerts_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/financial/alerts")
    assert res.status_code == 200
    codes = {a["code"] for a in res.json()["alerts"]}
    assert "INVOICE_OVERDUE" in codes


def test_health_score_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/financial/health-score")
    assert res.status_code == 200
    data = res.json()
    assert 0 <= data["score"] <= 100
    assert len(data["components"]) == 5


def test_refresh_query_bypasses_cache(client_ctx):
    client, db, org = client_ctx
    first = client.get("/api/financial/kpis").json()["kpis"][0]["value"]

    from app.models import BankAccount

    account = db.query(BankAccount).filter(BankAccount.organization_id == org.id).first()
    account.balance = 77777.0
    db.commit()

    cached = client.get("/api/financial/kpis").json()["kpis"][0]["value"]
    assert cached == first
    refreshed = client.get("/api/financial/kpis?refresh=true").json()["kpis"][0]["value"]
    assert refreshed == 77777.0


def test_platform_overview_endpoint(client_ctx):
    client, *_ = client_ctx
    res = client.get("/api/platform/financial/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["organizations_total"] >= 1
    assert data["average_score"] is not None
    assert isinstance(data["organizations"], list)
    first = data["organizations"][0]
    assert set(first.keys()) >= {"organization_id", "name", "score", "grade", "sync_status"}
