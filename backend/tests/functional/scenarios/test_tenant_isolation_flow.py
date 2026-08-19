"""SCENARIO — Isolation tenant (complément)."""

from __future__ import annotations


def test_member_limited_vs_admin(api, functional_db):
    api.login_user("member")
    assert api.org_id == functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    # Membre connecté sur la même org que admin
    api.login_user("org_admin")
    assert api.org_id == functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]


def test_no_subscription_org_seeded(functional_db):
    org = functional_db["seed"]["organizations"]["ORG_NONE"]
    Session = functional_db["Session"]
    db = Session()
    try:
        from app.models_saas import Subscription

        row = db.query(Subscription).filter(Subscription.organization_id == org["id"]).first()
        assert row is None
    finally:
        db.close()
