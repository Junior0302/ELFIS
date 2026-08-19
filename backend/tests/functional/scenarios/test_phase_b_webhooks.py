"""Phase B — Webhooks Stripe simulés (WEBHOOK-001 … WEBHOOK-008)."""

from __future__ import annotations

from unittest.mock import patch

from app.billing.billing_models import ElfisBillingEvent, ElfisSubscription
from app.billing.billing_types import BillingEventStatus
from app.models_saas import Subscription
from tests.functional.helpers.phase_b import apply_synthetic_stripe_event, assert_safe_billing_body


def test_webhook_001_003_subscription_lifecycle(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_NONE"]["id"]
    db = Session()
    try:
        # Créer un abonnement legacy minimal pour checkout/sync
        legacy = Subscription(
            organization_id=org_id,
            plan="starter",
            status="incomplete",
            price=19.0,
            stripe_customer_id="cus_wh_none",
            stripe_subscription_id="sub_wh_none",
        )
        db.add(legacy)
        db.commit()

        apply_synthetic_stripe_event(
            db,
            event_type="customer.subscription.created",
            organization_id=org_id,
            stripe_sub_id="sub_wh_none",
            stripe_customer_id="cus_wh_none",
            status="trialing",
            event_id="evt_wh_created",
        )
        apply_synthetic_stripe_event(
            db,
            event_type="customer.subscription.updated",
            organization_id=org_id,
            stripe_sub_id="sub_wh_none",
            stripe_customer_id="cus_wh_none",
            status="active",
            event_id="evt_wh_updated",
        )
        elfis = (
            db.query(ElfisSubscription)
            .filter(ElfisSubscription.organization_id == org_id, ElfisSubscription.is_current.is_(True))
            .first()
        )
        assert elfis is not None
        assert elfis.status == "active"
    finally:
        db.close()


def test_webhook_004_005_payment_succeeded_failed(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        apply_synthetic_stripe_event(
            db,
            event_type="invoice.payment_failed",
            organization_id=org_id,
            status="past_due",
            event_id="evt_wh_pay_fail",
        )
        legacy = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        assert legacy.status == "past_due"
        apply_synthetic_stripe_event(
            db,
            event_type="invoice.payment_succeeded",
            organization_id=org_id,
            status="active",
            event_id="evt_wh_pay_ok",
        )
        db.refresh(legacy)
        assert legacy.status == "active"
    finally:
        db.close()


def test_webhook_006_subscription_deleted(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_CANCELLED"]["id"]
    db = Session()
    try:
        apply_synthetic_stripe_event(
            db,
            event_type="customer.subscription.deleted",
            organization_id=org_id,
            status="canceled",
            event_id="evt_wh_deleted",
        )
        legacy = db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        assert legacy.status == "canceled"
    finally:
        db.close()


def test_webhook_007_duplicate_idempotent(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        apply_synthetic_stripe_event(
            db,
            event_type="customer.subscription.updated",
            organization_id=org_id,
            status="active",
            event_id="evt_wh_dup",
        )
        apply_synthetic_stripe_event(
            db,
            event_type="customer.subscription.updated",
            organization_id=org_id,
            status="active",
            event_id="evt_wh_dup",
        )
        rows = db.query(ElfisBillingEvent).filter(ElfisBillingEvent.provider_event_id == "evt_wh_dup").all()
        assert len(rows) == 1
        assert rows[0].status == BillingEventStatus.PROCESSED
    finally:
        db.close()


def test_webhook_008_invalid_signature_rejected(api):
    r = api.client.post(
        "/api/subscriptions/webhook",
        content=b'{"id":"evt_bad","type":"customer.subscription.updated"}',
        headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=bad"},
    )
    assert r.status_code in (400, 401, 403, 503)
    body = r.json()
    assert_safe_billing_body(body)
    assert r.headers.get("X-Request-Id")


def test_webhook_alias_route_same_handler(api):
    """Les deux routes webhook partagent le même traitement (signature requise)."""
    payload = b'{"id":"evt_alias","type":"invoice.payment_succeeded"}'
    headers = {"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=bad"}
    r1 = api.client.post("/api/subscriptions/webhook", content=payload, headers=headers)
    r2 = api.client.post("/api/webhooks/stripe", content=payload, headers=headers)
    assert r1.status_code == r2.status_code
    assert r1.status_code in (400, 401, 403, 503)


def test_webhook_001_checkout_completed_via_post_process(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_NONE"]["id"]
    db = Session()
    try:
        legacy = (
            db.query(Subscription).filter(Subscription.organization_id == org_id).first()
        )
        if legacy is None:
            legacy = Subscription(
                organization_id=org_id,
                plan="starter",
                status="incomplete",
                price=19.0,
                stripe_customer_id="cus_co",
                stripe_subscription_id="sub_co",
            )
            db.add(legacy)
            db.commit()
        apply_synthetic_stripe_event(
            db,
            event_type="checkout.session.completed",
            organization_id=org_id,
            stripe_sub_id=legacy.stripe_subscription_id or "sub_co",
            stripe_customer_id=legacy.stripe_customer_id or "cus_co",
            status="trialing",
            event_id="evt_wh_checkout",
            extra_object={"object": "checkout.session", "mode": "subscription"},
        )
        events = db.query(ElfisBillingEvent).filter(ElfisBillingEvent.provider_event_id == "evt_wh_checkout").all()
        assert len(events) >= 1
        summary = str(events[0].payload_summary or {})
        assert "card" not in summary.lower()
    finally:
        db.close()
