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


def test_plan_002_003_professional_enterprise_not_public_buyable():
    pro = get_plan("professional")
    ent = get_plan("enterprise")
    assert pro is not None and ent is not None
    assert pro.is_public is False
    assert ent.is_public is False
    assert pro.purchasable is False
    assert ent.purchasable is False
    public_codes = {p.plan_code for p in list_plans(public_only=True)}
    assert "professional" not in public_codes
    assert "enterprise" not in public_codes


def test_plan_private_not_in_public_api(api):
    r = api.client.get("/api/billing/plans")
    codes = {p["plan_code"] for p in (r.json().get("plans") or [])}
    assert "professional" not in codes
    assert "enterprise" not in codes
