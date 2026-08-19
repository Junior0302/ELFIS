"""Publication d'événements métier Billing (payload limité, sans secrets Stripe)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.billing.billing_types import SubscriptionStatus
from app.billing.plan_registry import default_plan_code, plan_code_for_stripe_price
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames

logger = logging.getLogger(__name__)

STRIPE_TO_BILLING_EVENT: dict[str, str] = {
    "checkout.session.completed": EventNames.BILLING_SUBSCRIPTION_CREATED,
    "customer.subscription.created": EventNames.BILLING_SUBSCRIPTION_CREATED,
    "customer.subscription.updated": EventNames.BILLING_SUBSCRIPTION_UPDATED,
    "customer.subscription.deleted": EventNames.BILLING_SUBSCRIPTION_CANCELLED,
    "invoice.payment_succeeded": EventNames.BILLING_SUBSCRIPTION_PAYMENT_SUCCEEDED,
    "invoice.payment_failed": EventNames.BILLING_SUBSCRIPTION_PAYMENT_FAILED,
    "invoice.upcoming": EventNames.BILLING_SUBSCRIPTION_UPDATED,
    "customer.subscription.trial_will_end": EventNames.BILLING_SUBSCRIPTION_TRIAL_ENDING,
}


def _payload(organization_id: int, subscription, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    plan_code = default_plan_code()
    status = None
    sub_id = None
    trial_ends = None
    period_ends = None
    cancel_at = False
    if subscription is not None:
        sub_id = getattr(subscription, "subscription_id", None)
        status = getattr(subscription, "status", None)
        trial_ends = getattr(subscription, "trial_ends_at", None)
        period_ends = getattr(subscription, "current_period_ends_at", None)
        cancel_at = bool(getattr(subscription, "cancel_at_period_end", False))
        price = getattr(subscription, "stripe_price_id", None)
        plan_code = plan_code_for_stripe_price(price) or plan_code
    data: dict[str, Any] = {
        "organization_id": organization_id,
        "subscription_id": sub_id,
        "plan_code": plan_code,
        "status": status,
        "trial_ends_at": trial_ends.isoformat() + "Z" if trial_ends else None,
        "current_period_ends_at": period_ends.isoformat() + "Z" if period_ends else None,
        "cancel_at_period_end": cancel_at,
    }
    if extra:
        data.update(extra)
    return data


def publish_billing_domain_event(
    db: Session,
    event_name: str,
    organization_id: int,
    subscription=None,
    *,
    extra: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> None:
    try:
        from app.events import safe_publish

        corr = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
        sub_id = getattr(subscription, "subscription_id", None) if subscription else None
        safe_publish(
            db,
            DomainEvent(
                event_name=event_name,
                organization_id=organization_id,
                aggregate_type="subscription",
                aggregate_id=str(sub_id) if sub_id else str(organization_id),
                payload=_payload(organization_id, subscription, extra=extra),
                correlation_id=corr,
                idempotency_key=f"{event_name}:{organization_id}:{sub_id or 'none'}:{corr}",
            ),
            commit=False,
        )
    except Exception:
        logger.exception("billing_event_publish_failed name=%s org=%s", event_name, organization_id)


def publish_billing_event_for_stripe(
    db: Session,
    *,
    stripe_event_type: str,
    organization_id: int,
    subscription=None,
) -> None:
    event_name = STRIPE_TO_BILLING_EVENT.get(stripe_event_type)
    if not event_name:
        return

    if subscription is not None:
        status = getattr(subscription, "status", None)
        if stripe_event_type == "customer.subscription.updated":
            if status == SubscriptionStatus.TRIALING:
                event_name = EventNames.BILLING_SUBSCRIPTION_TRIAL_STARTED
            elif status == SubscriptionStatus.ACTIVE:
                event_name = EventNames.BILLING_SUBSCRIPTION_ACTIVATED
            elif status == SubscriptionStatus.PAST_DUE:
                event_name = EventNames.BILLING_SUBSCRIPTION_PAST_DUE
            elif getattr(subscription, "cancel_at_period_end", False):
                event_name = EventNames.BILLING_SUBSCRIPTION_CANCEL_SCHEDULED
            elif status == SubscriptionStatus.SUSPENDED:
                event_name = EventNames.BILLING_SUBSCRIPTION_SUSPENDED

    publish_billing_domain_event(db, event_name, organization_id, subscription)
    publish_billing_domain_event(
        db, EventNames.BILLING_ENTITLEMENTS_UPDATED, organization_id, subscription
    )


def post_process_legacy_webhook(
    db: Session, event: dict[str, Any], *, payload_hash: str | None = None
) -> None:
    """Après apply_webhook_event legacy : sync elfis_* + events (sans re-appliquer Stripe)."""
    from app.billing.billing_repository import BillingRepository
    from app.billing.billing_security import summarize_webhook_payload
    from app.billing.billing_types import BillingEventStatus
    from app.billing.subscription_service import SubscriptionService
    from app.billing.webhooks.stripe_webhook_handler import StripeWebhookHandler

    handler = StripeWebhookHandler(db)
    org_id = handler._extract_organization_id(event)
    provider_event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    repo = BillingRepository(db)

    if provider_event_id:
        existing = repo.get_event_by_provider_id(provider_event_id)
        if existing and existing.status == BillingEventStatus.PROCESSED:
            return

    row = repo.get_event_by_provider_id(provider_event_id) if provider_event_id else None
    if not row:
        row = repo.create_event(
            provider="stripe",
            provider_event_id=provider_event_id or None,
            event_type=event_type,
            organization_id=org_id,
            payload_hash=payload_hash,
            payload_summary=summarize_webhook_payload(event),
        )
        db.flush()

    sub = None
    if org_id:
        sub = SubscriptionService(db).sync_from_legacy(org_id, rebuild=True)
        if row and sub:
            row.organization_id = org_id
            row.subscription_id = sub.subscription_id
        publish_billing_event_for_stripe(
            db,
            stripe_event_type=event_type,
            organization_id=org_id,
            subscription=sub,
        )
    if row:
        repo.mark_event_processed(row)
