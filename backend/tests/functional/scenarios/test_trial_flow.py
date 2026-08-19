"""SCENARIO 2 — Essai gratuit."""

from __future__ import annotations


def test_trial_subscription_visible(api, functional_db):
    api.login_user("trial")
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_TRIAL"]["id"]
    db = Session()
    try:
        from app.models_saas import Subscription
        from app.billing.billing_models import ElfisSubscription

        legacy = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        assert legacy is not None
        assert legacy.status == "trialing"
        assert legacy.trial_end is not None
        assert legacy.trial_end > legacy.trial_start

        elfis = (
            db.query(ElfisSubscription)
            .filter(
                ElfisSubscription.organization_id == org_id,
                ElfisSubscription.is_current.is_(True),
            )
            .first()
        )
        # Sync peut avoir produit une ligne V1
        if elfis is not None:
            assert elfis.status == "trialing"
    finally:
        db.close()


def test_active_subscription_starter(api, functional_db):
    api.login_user("active")
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        from app.models_saas import Subscription

        legacy = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        assert legacy is not None
        assert legacy.status == "active"
        assert float(legacy.price) == 19.0
    finally:
        db.close()
