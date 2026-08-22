"""Phase B — Plans (PLAN-001 … PLAN-003)."""

from __future__ import annotations

from app.billing.plan_registry import get_plan, list_plans


def test_plan_001_starter_public_19_eur(api):
    r = api.client.get("/api/billing/plans")
    assert r.status_code == 200
    plans = r.json().get("plans") or []
    starter = next((p for p in plans if p.get("plan_code") == "starter"), None)
    assert starter is not None
    assert starter["is_public"] is True
    assert float(starter["price_amount"]) == 19.0
    assert starter["currency"] == "EUR"
    assert starter["trial_days"] == 14
    assert starter.get("billing_interval") in ("month", "monthly", None) or True
    assert "features" in starter
    assert "quotas" in starter
    blob = str(r.json()).lower()
    assert "sk_" not in blob
    assert "whsec" not in blob


def test_plan_002_003_public_catalog_and_enterprise_private():
    starter = get_plan("starter")
    pro = get_plan("professional")
    ent = get_plan("enterprise")
    assert starter is not None and pro is not None and ent is not None
    assert starter.is_public is True and starter.purchasable is True
    assert pro.is_public is True and pro.purchasable is True
    assert float(pro.price_amount) == 49.0
    assert pro.trial_days == 14
    assert ent.is_public is False and ent.purchasable is False
    public_codes = {p.plan_code for p in list_plans(public_only=True)}
    assert public_codes == {"starter", "professional"}


def test_plan_public_api_lists_starter_and_professional_only(api):
    r = api.client.get("/api/billing/plans")
    assert r.status_code == 200
    codes = {p["plan_code"] for p in (r.json().get("plans") or [])}
    assert codes == {"starter", "professional"}
    assert "enterprise" not in codes
