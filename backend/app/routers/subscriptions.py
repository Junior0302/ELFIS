from __future__ import annotations

import hashlib

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import StripeWebhookEvent, Subscription
from app.services.stripe_billing import (
    apply_webhook_event,
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
    get_organization_subscription,
    serialize_subscription,
    sync_checkout_session,
    sync_subscription_from_stripe,
)
from app.subscriptions.access import get_subscription_access, serialize_access
from app.subscriptions.consent import record_checkout_consent
from app.subscriptions.constants import PLANS, PLAN_COMPTAPILOT_MONTHLY
from app.subscriptions.notifications import run_trial_reminders

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
webhook_alias_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SyncIn(BaseModel):
    session_id: str | None = Field(default=None)


class CheckoutIn(BaseModel):
    automatic_renewal_accepted: bool = False
    terms_accepted: bool = False


def _platform_bypass(auth: AuthContext) -> bool:
    user = auth.user
    if not user or user.status != "active":
        return False
    return bool(
        user.is_platform_admin or user.email.lower() in settings.platform_admin_email_set
    )


@router.get("/current")
def current_subscription(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    organization_id = auth.require_organization_id()
    access = get_subscription_access(db, organization_id, user=auth.user)
    payload = serialize_access(access)
    row = get_organization_subscription(db, organization_id)
    if row and row.stripe_price_id:
        payload["stripe_price_id"] = row.stripe_price_id
    if row and row.past_due_since:
        payload["past_due_since"] = row.past_due_since
    return {"subscription": payload}


@router.get("/plan")
def subscription_plan_info():
    plan = PLANS[PLAN_COMPTAPILOT_MONTHLY]
    return {
        "plan_code": PLAN_COMPTAPILOT_MONTHLY,
        "name": plan["name"],
        "price_amount_cents": plan["price_amount"],
        "currency": plan["currency"],
        "trial_days": settings.stripe_trial_days,
        "feature_labels": plan["feature_labels"],
        "terms_version": settings.subscription_terms_version,
    }


@router.post("/checkout")
def subscription_checkout(
    request: Request,
    payload: CheckoutIn = Body(default_factory=CheckoutIn),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    record_checkout_consent(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        automatic_renewal_accepted=payload.automatic_renewal_accepted,
        terms_accepted=payload.terms_accepted,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    url, session_id = create_checkout_session(
        db,
        organization_id=organization_id,
        customer_email=auth.user.email,
    )
    # Lier le consentement à la session
    from app.models_saas import SubscriptionConsent

    consent = (
        db.query(SubscriptionConsent)
        .filter(
            SubscriptionConsent.user_id == auth.user.id,
            SubscriptionConsent.organization_id == organization_id,
        )
        .order_by(SubscriptionConsent.id.desc())
        .first()
    )
    if consent and session_id:
        consent.checkout_session_id = session_id
        db.add(consent)
    db.commit()
    return {"url": url, "session_id": session_id}


@router.post("/portal")
def subscription_portal(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    return {"url": create_portal_session(db, organization_id=organization_id)}


@router.post("/sync")
def subscription_sync(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    payload: SyncIn = Body(default_factory=SyncIn),
):
    """Rattrapage après Checkout : lit le statut réel chez Stripe sans attendre le webhook."""
    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()
    cleaned = (payload.session_id or "").strip() or None
    try:
        row = sync_checkout_session(db, organization_id=organization_id, session_id=cleaned)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail={
                "code": "stripe_sync_failed",
                "message": f"Synchronisation impossible. Réessayez dans un instant.",
            },
        ) from exc
    db.commit()
    access = get_subscription_access(db, organization_id, user=auth.user)
    return {"subscription": serialize_access(access)}


async def _handle_stripe_webhook(
    request: Request,
    stripe_signature: str | None,
    db: Session,
):
    raw = await request.body()
    event = construct_webhook_event(raw, stripe_signature)
    event_id = event.get("id") or ""
    event_type = event.get("type", "")
    obj = ((event.get("data") or {}).get("object") or {})
    object_id = ""
    if isinstance(obj, dict):
        object_id = str(obj.get("id") or "")
    payload_hash = hashlib.sha256(raw).hexdigest()

    marker = StripeWebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        stripe_object_id=object_id,
        status="received",
        attempt_count=1,
        payload_hash=payload_hash,
    )
    try:
        db.add(marker)
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}

    try:
        apply_webhook_event(db, event)
        marker.status = "processed"
        from datetime import datetime

        marker.processed_at = datetime.utcnow()
        db.add(marker)
        db.commit()
    except Exception as exc:
        db.rollback()
        # Recharger le marker si rollback
        existing = (
            db.query(StripeWebhookEvent)
            .filter(StripeWebhookEvent.stripe_event_id == event_id)
            .first()
        )
        if existing:
            existing.status = "failed"
            existing.last_error = str(exc)[:1000]
            existing.attempt_count = int(existing.attempt_count or 1) + 1
            db.add(existing)
            db.commit()
        raise
    return {"received": True, "duplicate": False}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    return await _handle_stripe_webhook(request, stripe_signature, db)


@webhook_alias_router.post("/stripe")
async def stripe_webhook_alias(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    return await _handle_stripe_webhook(request, stripe_signature, db)


class CronIn(BaseModel):
    token: str = ""


@router.post("/jobs/trial-reminders")
def job_trial_reminders(
    payload: CronIn,
    db: Session = Depends(get_db),
):
    expected = (settings.subscription_cron_token or "").strip()
    if not expected or payload.token != expected:
        raise HTTPException(403, detail={"code": "ADMIN_PERMISSION_REQUIRED", "message": "Token invalide"})
    j7 = run_trial_reminders(db, days_before=7)
    j3 = run_trial_reminders(db, days_before=3)
    j1 = run_trial_reminders(db, days_before=1)
    db.commit()
    return {"ok": True, "reminders": {"j7": j7, "j3": j3, "j1": j1}}
