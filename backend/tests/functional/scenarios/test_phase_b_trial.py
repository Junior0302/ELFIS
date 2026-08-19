"""Phase B — Essai gratuit (TRIAL-001 … TRIAL-003)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.billing.billing_types import FeatureCodes
from app.billing.entitlement_service import EntitlementService
from app.billing.subscription_service import SubscriptionService
from app.models_saas import Subscription
from tests.functional.helpers.phase_b import assert_safe_billing_body, enable_enforcement


def test_trial_001_002_active_14_days_auto_renew(api):
    api.login_user("trial")
    r = api.client.get("/api/billing/subscription", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_billing_body(body)
    assert body.get("status") in ("trialing", "active")
    assert body.get("trial_days") == 14
    assert float(body.get("price") or 0) == 19.0
    assert body.get("currency") == "EUR"
    assert body.get("plan_code") == "starter"
    assert body.get("will_renew_automatically") is True
    disc = body.get("disclosure") or {}
    assert "14" in str(disc.get("trial") or "")
    assert "19" in str(disc.get("trial") or "")
    # Fin d'essai future (pas fragile à la seconde)
    ends = body.get("trial_ends_at")
    assert ends
    assert int(str(ends)[:4]) >= 2026


def test_trial_features_available_with_enforcement(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_TRIAL"]["id"]
    db = Session()
    try:
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        EntitlementService(db).require(org_id, FeatureCodes.DOCUMENTS_UPLOAD)
        EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
    finally:
        db.close()


def test_trial_003_expired_blocks_costly(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_TRIAL"]["id"]
    db = Session()
    try:
        from app.billing.billing_exceptions import FeatureNotAvailableError

        row = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        assert row is not None
        row.status = "canceled"
        row.trial_end = datetime.utcnow() - timedelta(days=1)
        row.canceled_at = datetime.utcnow() - timedelta(hours=1)
        row.cancel_at_period_end = False
        db.flush()
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        db.commit()
        with __import__("pytest").raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
    finally:
        db.close()
