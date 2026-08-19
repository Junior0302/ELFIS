"""SCENARIO 8 — Billing / quotas."""

from __future__ import annotations

from app.billing.billing_types import QuotaCodes
from app.billing.quota_service import QuotaService
from app.config import settings


def test_quota_near_limit_profile(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_QUOTA_NEAR"]["id"]
    db = Session()
    try:
        qs = QuotaService(db)
        result = qs.check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=1)
        assert result.used_value >= 80
        if result.limit_value:
            assert result.used_value / result.limit_value >= 0.8
    finally:
        db.close()


def test_quota_at_limit_enforcement(functional_db, monkeypatch):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_QUOTA_FULL"]["id"]
    monkeypatch.setattr(settings, "elfis_billing_enforce_quotas", True)
    db = Session()
    try:
        qs = QuotaService(db)
        result = qs.check(org_id, QuotaCodes.DOCUMENTS_PROCESSED_MONTH, amount=1)
        # At limit → not allowed when enforce on
        if result.limit_value is not None and result.used_value >= result.limit_value:
            assert result.allowed is False
    finally:
        db.close()
        monkeypatch.setattr(settings, "elfis_billing_enforce_quotas", False)


def test_past_due_and_cancelled_seeded(functional_db):
    Session = functional_db["Session"]
    db = Session()
    try:
        from app.models_saas import Subscription

        past = functional_db["seed"]["organizations"]["ORG_PAST_DUE"]["id"]
        canc = functional_db["seed"]["organizations"]["ORG_CANCELLED"]["id"]
        s1 = db.query(Subscription).filter(Subscription.organization_id == past).first()
        s2 = db.query(Subscription).filter(Subscription.organization_id == canc).first()
        assert s1 is not None and s1.status == "past_due"
        assert s2 is not None and s2.cancel_at_period_end is True
    finally:
        db.close()
