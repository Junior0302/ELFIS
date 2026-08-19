"""Helpers Phase B — Billing / webhooks / quotas."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.billing.billing_events import post_process_legacy_webhook
from app.billing.subscription_service import SubscriptionService
from app.config import settings
from app.models_saas import Subscription


def assert_safe_billing_body(body: dict[str, Any]) -> None:
    blob = str(body).lower()
    for forbidden in (
        "sk_live",
        "sk_test",
        "whsec_",
        "traceback",
        "card_number",
        "cvc",
        "authorization",
        "bearer ",
        "password",
    ):
        assert forbidden not in blob, f"fuite suspecte: {forbidden}"


def set_past_due_since(db: Session, organization_id: int, *, days_ago: int) -> Subscription:
    row = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )
    assert row is not None
    row.status = "past_due"
    row.past_due_since = datetime.utcnow() - timedelta(days=days_ago)
    db.flush()
    SubscriptionService(db).sync_from_legacy(organization_id, rebuild=True)
    db.commit()
    return row


def apply_synthetic_stripe_event(
    db: Session,
    *,
    event_type: str,
    organization_id: int,
    stripe_sub_id: str | None = None,
    stripe_customer_id: str | None = None,
    status: str = "active",
    event_id: str | None = None,
    extra_object: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Simule le post-traitement Billing après webhook (sans réseau Stripe)."""
    sub_id = stripe_sub_id or f"sub_phase_b_{organization_id}"
    cus_id = stripe_customer_id or f"cus_phase_b_{organization_id}"
    obj: dict[str, Any] = {
        "id": sub_id if "subscription" in event_type or event_type.startswith("customer.") else f"in_{uuid4().hex[:8]}",
        "object": "subscription" if "subscription" in event_type else "invoice",
        "customer": cus_id,
        "status": status,
        "metadata": {"organization_id": str(organization_id)},
    }
    if event_type.startswith("invoice."):
        obj["subscription"] = sub_id
    if extra_object:
        obj.update(extra_object)
    event = {
        "id": event_id or f"evt_phase_b_{uuid4().hex[:12]}",
        "type": event_type,
        "data": {"object": obj},
        "livemode": False,
    }
    # Mettre à jour legacy si subscription connue
    legacy = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )
    if legacy:
        legacy.stripe_customer_id = cus_id
        legacy.stripe_subscription_id = sub_id
        if event_type in {"customer.subscription.updated", "customer.subscription.created", "checkout.session.completed"}:
            legacy.status = status
        if event_type == "invoice.payment_failed":
            legacy.status = "past_due"
            legacy.past_due_since = datetime.utcnow()
        if event_type in {"invoice.payment_succeeded", "invoice.paid"}:
            legacy.status = "active"
            legacy.past_due_since = None
        if event_type == "customer.subscription.deleted":
            legacy.status = "canceled"
            legacy.canceled_at = datetime.utcnow()
        db.flush()

    post_process_legacy_webhook(db, event, payload_hash=f"hash_{event['id']}")
    db.commit()
    return event


def enable_enforcement(monkeypatch, *, entitlements: bool = True, quotas: bool = True) -> None:
    monkeypatch.setattr(settings, "elfis_billing_enforce_entitlements", entitlements)
    monkeypatch.setattr(settings, "elfis_billing_enforce_quotas", quotas)


def disable_enforcement(monkeypatch) -> None:
    monkeypatch.setattr(settings, "elfis_billing_enforce_entitlements", False)
    monkeypatch.setattr(settings, "elfis_billing_enforce_quotas", False)
