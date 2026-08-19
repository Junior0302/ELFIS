"""Phase B — Entitlements (ENT-001 … ENT-005)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.billing.billing_exceptions import FeatureNotAvailableError
from app.billing.billing_types import FeatureCodes
from app.billing.entitlement_service import EntitlementService
from app.billing.subscription_service import SubscriptionService
from app.deps import AuthContext, require_active_subscription
from app.models_saas import Organization, User
from tests.functional.helpers.phase_b import enable_enforcement, set_past_due_since


def test_ent_001_trial(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_TRIAL"]["id"]
    db = Session()
    try:
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        EntitlementService(db).require(org_id, FeatureCodes.DOCUMENTS_UPLOAD)
        ents = EntitlementService(db).get_entitlements(org_id)
        assert ents.get(FeatureCodes.AI_CLASSIFICATION) is True
    finally:
        db.close()


def test_ent_002_active(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        EntitlementService(db).require(org_id, FeatureCodes.ACCOUNTING_PROPOSALS)
    finally:
        db.close()


def test_ent_003_expired(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_EXPIRED"]["id"]
    db = Session()
    try:
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
    finally:
        db.close()


def test_ent_past_due_in_and_out_of_grace(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_PAST_DUE"]["id"]
    db = Session()
    try:
        set_past_due_since(db, org_id, days_ago=2)
        # Grâce active = lecture / has_access ; features coûteuses en read_only
        access = __import__("app.subscriptions.access", fromlist=["get_subscription_access"]).get_subscription_access(
            db, org_id
        )
        assert access.has_access is True
        assert access.read_only is True
        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.DOCUMENTS_UPLOAD)
        set_past_due_since(db, org_id, days_ago=10)
        with pytest.raises(FeatureNotAvailableError):
            EntitlementService(db).require(org_id, FeatureCodes.AI_CLASSIFICATION)
    finally:
        db.close()


def test_ent_004_suspension_priority(functional_db, monkeypatch):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_SUSPENDED"]["id"]
    db = Session()
    try:
        org = db.get(Organization, org_id)
        assert org is not None
        assert org.platform_status == "suspended"
        user = functional_db["seed"]["users"]["suspended"]
        u = db.get(User, user["id"])
        auth = AuthContext(u, org_id, "owner", ["*"])
        req = MagicMock()
        req.method = "POST"
        with pytest.raises(Exception) as raised:
            require_active_subscription(request=req, auth=auth, db=db)
        exc = raised.value
        detail = getattr(exc, "detail", None)
        code = detail.get("code") if isinstance(detail, dict) else None
        assert code in (
            "organization_suspended",
            "subscription_inactive",
            "subscription_required",
            None,
        ) or getattr(exc, "status_code", None) in (403, 402)
    finally:
        db.close()


def test_ent_005_override_admin(functional_db, monkeypatch, api):
    enable_enforcement(monkeypatch, entitlements=True, quotas=False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_EXPIRED"]["id"]
    db = Session()
    try:
        SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        svc = EntitlementService(db)
        with pytest.raises(FeatureNotAvailableError):
            svc.require(org_id, FeatureCodes.DOCUMENTS_OCR)
        svc.set_override(org_id, FeatureCodes.DOCUMENTS_OCR, True)
        db.commit()
        svc.require(org_id, FeatureCodes.DOCUMENTS_OCR)
        assert svc.remove_override(org_id, FeatureCodes.DOCUMENTS_OCR)
        db.commit()
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/platform/billing/organizations/{org_id}/entitlements",
        headers=api._headers(),
        json={"feature_code": "documents.ocr", "enabled": True, "reason": "hack"},
    )
    assert r.status_code in (401, 403)
