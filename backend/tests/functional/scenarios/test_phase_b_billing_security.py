"""Phase B — Sécurité Billing (BILLSEC-003/004, checkout, portal)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.billing.billing_exceptions import BillingValidationError
from app.billing.billing_security import assert_plan_purchasable
from app.billing.plan_registry import get_plan
from tests.functional.helpers.phase_b import assert_safe_billing_body


def test_checkout_002_non_public_and_unknown_plans_refused():
    with pytest.raises(BillingValidationError):
        assert_plan_purchasable("enterprise")
    with pytest.raises(BillingValidationError):
        assert_plan_purchasable("unknown_plan_xyz")
    with pytest.raises(BillingValidationError):
        assert_plan_purchasable("professional")


def test_checkout_002_professional_allowed_when_stripe_configured():
    from app.config import settings

    with patch.object(settings, "stripe_price_professional_monthly", "price_recette_pro_test"):
        price = assert_plan_purchasable("professional")
    assert price == "price_recette_pro_test"


def test_checkout_002_enterprise_refused_even_with_stripe_price():
    from app.config import settings

    with patch.object(settings, "stripe_price_enterprise_monthly", "price_recette_ent_test"):
        with pytest.raises(BillingValidationError):
            assert_plan_purchasable("enterprise")


def test_checkout_001_mock_org_none(api, monkeypatch):
    api.login_user("no_sub")
    monkeypatch.setattr(
        "app.config.settings.stripe_price_pro",
        "price_recette_starter_test",
        raising=False,
    )
    monkeypatch.setattr(
        "app.config.settings.stripe_price_starter_monthly",
        "price_recette_starter_test",
        raising=False,
    )
    with patch(
        "app.services.stripe_billing.create_checkout_session",
        return_value=("https://checkout.stripe.test/session/mock", "cs_test_mock"),
    ):
        r = api.client.post(
            "/api/billing/checkout",
            headers=api._headers(),
            json={
                "plan_code": "starter",
                "automatic_renewal_accepted": True,
                "terms_accepted": True,
            },
        )
    assert r.status_code in (200, 201)
    body = r.json()
    assert_safe_billing_body(body)
    assert "mock" in (body.get("url") or "") or body.get("session_id")


def test_checkout_003_enterprise_checkout_api_refused(api, monkeypatch):
    api.login_user("no_sub")
    monkeypatch.setattr(
        "app.config.settings.stripe_price_enterprise_monthly",
        "price_recette_ent_test",
        raising=False,
    )
    r = api.client.post(
        "/api/billing/checkout",
        headers=api._headers(),
        json={
            "plan_code": "enterprise",
            "automatic_renewal_accepted": True,
            "terms_accepted": True,
        },
    )
    assert r.status_code in (400, 403)


def test_portal_001_002_active_and_pastdue(api):
    for user in ("active", "pastdue"):
        api.login_user(user)
        with patch(
            "app.services.stripe_billing.create_portal_session",
            return_value=f"https://billing.stripe.test/portal/{user}",
        ):
            r = api.client.post("/api/billing/customer-portal", headers=api._headers())
        assert r.status_code in (200, 201)
        assert_safe_billing_body(r.json())


def test_billsec_003_004_history_no_stripe_secrets(api):
    api.login_user("active")
    r = api.client.get("/api/billing/history", headers=api._headers())
    assert r.status_code == 200
    blob = str(r.json()).lower()
    for forbidden in ("sk_live", "sk_test", "whsec", "card_number", "cvc", "password"):
        assert forbidden not in blob


def test_member_cannot_checkout(api):
    api.login_user("member")
    r = api.client.post(
        "/api/billing/checkout",
        headers=api._headers(),
        json={
            "plan_code": "starter",
            "automatic_renewal_accepted": True,
            "terms_accepted": True,
        },
    )
    assert r.status_code in (401, 403)


def test_starter_registry_defaults():
    starter = get_plan("starter")
    assert starter is not None
    assert float(starter.price_amount) == 19.0
    assert starter.trial_days == 14
    assert starter.is_public is True
    assert starter.purchasable is True
