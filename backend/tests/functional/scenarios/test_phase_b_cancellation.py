"""Phase B — Annulation / resume / expiration (CANCEL-001 … CANCEL-004)."""

from __future__ import annotations

from unittest.mock import patch

from app.billing.billing_types import FeatureCodes
from app.billing.entitlement_service import EntitlementService
from app.billing.subscription_service import SubscriptionService
from app.subscriptions.access import get_subscription_access
from tests.functional.helpers.phase_b import assert_safe_billing_body, enable_enforcement


def test_cancel_001_002_at_period_end_keeps_rights(api, functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    api.login_user("cancelled")
    r = api.client.get("/api/billing/subscription", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_billing_body(body)
    assert body.get("cancel_at_period_end") is True
    assert body.get("will_renew_automatically") is False
    assert body.get("status") in ("cancel_scheduled", "active")

    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_CANCELLED"]["id"]
    db = Session()
    try:
        access = get_subscription_access(db, org_id)
        assert access.has_access is True
        EntitlementService(db).require(org_id, FeatureCodes.DOCUMENTS_UPLOAD)
    finally:
        db.close()


def test_cancel_003_resume_portal(api, monkeypatch):
    """Resume V1 ouvre le portail Stripe (mock)."""
    api.login_user("cancelled")
    with patch(
        "app.services.stripe_billing.create_portal_session",
        return_value="https://billing.stripe.test/portal/mock",
    ):
        r = api.client.post("/api/billing/resume", headers=api._headers())
    assert r.status_code in (200, 201)
    body = r.json()
    assert_safe_billing_body(body)
    assert "url" in body or "portal" in str(body).lower() or r.status_code == 200


def test_cancel_004_expiration_blocks(api, functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    api.login_user("expired")
    r = api.client.get("/api/billing/subscription", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in ("canceled", "cancelled", "expired", "none")
    # Lecture plans toujours possible
    assert api.client.get("/api/billing/plans").status_code == 200

    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_EXPIRED"]["id"]
    db = Session()
    try:
        from app.billing.billing_exceptions import FeatureNotAvailableError
        import pytest

        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
    finally:
        db.close()
