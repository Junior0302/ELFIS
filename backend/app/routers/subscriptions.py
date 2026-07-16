from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import StripeWebhookEvent, Subscription
from app.services.stripe_billing import (
    apply_webhook_event,
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
    serialize_subscription,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _current(db: Session, organization_id: int) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )


@router.get("/current")
def current_subscription(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    return {"subscription": serialize_subscription(_current(db, organization_id))}


@router.post("/checkout")
def subscription_checkout(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    return {
        "url": create_checkout_session(
            db,
            organization_id=organization_id,
            customer_email=auth.user.email,
        )
    }


@router.post("/portal")
def subscription_portal(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    return {"url": create_portal_session(db, organization_id=organization_id)}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    event = construct_webhook_event(await request.body(), stripe_signature)
    event_id = event.get("id")
    event_type = event.get("type", "")
    marker = StripeWebhookEvent(stripe_event_id=event_id, event_type=event_type)
    try:
        db.add(marker)
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}

    try:
        apply_webhook_event(db, event)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"received": True, "duplicate": False}
