"""Phase B — Abonnement actif + sync legacy (SUB-001 … SUB-003)."""

from __future__ import annotations

from app.billing.billing_models import ElfisSubscription
from app.billing.billing_types import FeatureCodes
from app.billing.entitlement_service import EntitlementService
from app.billing.subscription_service import SubscriptionService
from app.models_saas import Subscription
from tests.functional.helpers.phase_b import assert_safe_billing_body, enable_enforcement


def test_sub_001_active_allows_features(api, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    api.login_user("active")
    r = api.client.get("/api/billing/subscription", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_billing_body(body)
    assert body.get("status") in ("active", "cancel_scheduled")
    assert body.get("plan_code") == "starter"
    assert float(body.get("price") or 0) == 19.0
    assert body.get("will_renew_automatically") is True
    assert body.get("next_billing_date")


def test_sub_002_003_legacy_and_elfis_synced(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        legacy = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        assert legacy is not None
        assert legacy.status == "active"
        elfis = (
            db.query(ElfisSubscription)
            .filter(ElfisSubscription.organization_id == org_id, ElfisSubscription.is_current.is_(True))
            .first()
        )
        if elfis is None:
            elfis = SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
            db.commit()
        assert elfis is not None
        assert elfis.legacy_subscription_id == legacy.id
        assert elfis.status in ("active", "trialing")
        assert elfis.stripe_customer_id == legacy.stripe_customer_id
        EntitlementService(db).get_entitlements(org_id)
        assert FeatureCodes.DOCUMENTS_UPLOAD in EntitlementService(db).get_entitlements(org_id)
    finally:
        db.close()
