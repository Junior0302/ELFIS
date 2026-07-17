from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Subscription, SubscriptionConsent
from app.subscriptions.access import get_subscription_access
from app.subscriptions.constants import (
    PRICE_AMOUNT_CENTS,
    TERMS_VERSION_DEFAULT,
)


def record_checkout_consent(
    db: Session,
    *,
    user_id: int,
    organization_id: int,
    automatic_renewal_accepted: bool,
    terms_accepted: bool,
    ip_address: str = "",
    user_agent: str = "",
    checkout_session_id: str = "",
    subscription_id: int | None = None,
) -> SubscriptionConsent:
    if not automatic_renewal_accepted or not terms_accepted:
        raise HTTPException(
            400,
            detail={
                "code": "consent_required",
                "message": "Vous devez accepter le renouvellement automatique et les conditions.",
            },
        )
    consent = SubscriptionConsent(
        user_id=user_id,
        organization_id=organization_id,
        subscription_id=subscription_id,
        consent_type="trial_checkout",
        terms_version=settings.subscription_terms_version or TERMS_VERSION_DEFAULT,
        price_amount=PRICE_AMOUNT_CENTS,
        currency="EUR",
        trial_days=settings.stripe_trial_days,
        automatic_renewal_accepted=True,
        terms_accepted=True,
        accepted_at=datetime.utcnow(),
        ip_address=(ip_address or "")[:64],
        user_agent=(user_agent or "")[:512],
        checkout_session_id=checkout_session_id or "",
    )
    db.add(consent)
    db.flush()
    return consent


def assert_trial_eligible(db: Session, organization_id: int, user=None) -> Subscription | None:
    access = get_subscription_access(db, organization_id, user=user)
    if access.has_access and access.subscription_status in {"trialing", "active", "cancel_scheduled"}:
        raise HTTPException(
            409,
            detail={
                "code": "SUBSCRIPTION_ALREADY_ACTIVE",
                "message": "Cette organisation possède déjà un abonnement actif",
                "action": "OPEN_PORTAL",
            },
        )
    return (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )


def trial_days_for_checkout(subscription: Subscription | None) -> int:
    """0 si essai déjà consommé (sauf admin_granted)."""
    if subscription is None:
        return settings.stripe_trial_days
    if subscription.trial_eligibility_status == "admin_granted":
        return settings.stripe_trial_days
    if subscription.trial_used:
        return 0
    return settings.stripe_trial_days

