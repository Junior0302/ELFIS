"""Phase B — Past due / grâce 7 jours (PASTDUE-001 … PASTDUE-003)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.billing.billing_exceptions import FeatureNotAvailableError
from app.billing.billing_types import FeatureCodes
from app.billing.entitlement_service import EntitlementService
from app.config import settings
from app.deps import AuthContext, require_active_subscription
from app.models_saas import User
from app.subscriptions.access import get_subscription_access
from tests.functional.helpers.phase_b import enable_enforcement, set_past_due_since


def test_pastdue_001_grace_active(api, functional_db):
    api.login_user("pastdue")
    r = api.client.get("/api/billing/subscription", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "past_due"
    # Grâce encore active (seed −2j, politique 7j)
    Session = functional_db["Session"]
    org_id = api.org_id
    db = Session()
    try:
        access = get_subscription_access(db, org_id)
        assert access.has_access is True
        assert access.read_only is True
    finally:
        db.close()


def test_pastdue_002_after_grace_blocks(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_PAST_DUE"]["id"]
    user_info = functional_db["seed"]["users"]["pastdue"]
    db = Session()
    try:
        set_past_due_since(db, org_id, days_ago=8)
        access = get_subscription_access(db, org_id)
        assert access.has_access is False
        u = db.get(User, user_info["id"])
        auth = AuthContext(u, org_id, "owner", ["*"])
        req = MagicMock()
        req.method = "GET"
        with pytest.raises(HTTPException) as raised:
            require_active_subscription(request=req, auth=auth, db=db)
        assert raised.value.status_code in (402, 403)
        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
    finally:
        db.close()


def test_pastdue_003_harmonized_7_days_day4_still_grace(functional_db, monkeypatch):
    """Régression : J+4 reste en grâce (politique unique 7 jours)."""
    monkeypatch.setattr(settings, "elfis_billing_past_due_grace_days", 7)
    monkeypatch.setattr(settings, "stripe_past_due_grace_days", 7)
    assert int(settings.elfis_billing_past_due_grace_days) == 7
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_PAST_DUE"]["id"]
    db = Session()
    try:
        set_past_due_since(db, org_id, days_ago=4)
        access = get_subscription_access(db, org_id)
        assert access.has_access is True
        assert access.read_only is True
        set_past_due_since(db, org_id, days_ago=6)
        assert get_subscription_access(db, org_id).has_access is True
        set_past_due_since(db, org_id, days_ago=8)
        assert get_subscription_access(db, org_id).has_access is False
    finally:
        db.close()


def test_pastdue_portal_still_reachable(api, monkeypatch):
    api.login_user("pastdue")
    from unittest.mock import patch

    with patch(
        "app.services.stripe_billing.create_portal_session",
        return_value="https://billing.stripe.test/portal/pastdue",
    ):
        r = api.client.post("/api/billing/customer-portal", headers=api._headers())
    assert r.status_code in (200, 201)
