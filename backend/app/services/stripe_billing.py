from __future__ import annotations

from datetime import datetime
from typing import Any

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Organization, Subscription

STRIPE_SUBSCRIPTION_STATUSES = {
    "incomplete",
    "incomplete_expired",
    "trialing",
    "active",
    "past_due",
    "canceled",
    "unpaid",
    "paused",
}
PRO_PLAN_STATUSES = {"trialing", "active", "past_due", "unpaid", "paused"}


def _require_stripe(*, webhook: bool = False) -> None:
    missing = []
    if not settings.stripe_secret_key:
        missing.append("STRIPE_SECRET_KEY")
    if webhook and not settings.stripe_webhook_secret:
        missing.append("STRIPE_WEBHOOK_SECRET")
    if not webhook and not settings.stripe_price_pro:
        missing.append("STRIPE_PRICE_PRO")
    if missing:
        raise HTTPException(
            503,
            detail={
                "code": "stripe_not_configured",
                "message": "Configuration Stripe incomplète",
                "missing": missing,
            },
        )
    stripe.api_key = settings.stripe_secret_key


def construct_webhook_event(payload: bytes, signature: str | None) -> dict[str, Any]:
    _require_stripe(webhook=True)
    if not signature:
        raise HTTPException(
            400,
            detail={"code": "stripe_signature_missing", "message": "Signature Stripe absente"},
        )
    try:
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(
            400,
            detail={"code": "stripe_signature_invalid", "message": "Signature Stripe invalide"},
        ) from exc


def _subscription_for_org(db: Session, organization_id: int) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )


def serialize_subscription(subscription: Subscription | None) -> dict[str, Any]:
    if not subscription:
        return {
            "plan": "pro",
            "price_eur": 19,
            "status": "none",
            "trial_start": None,
            "trial_end": None,
            "current_period_start": None,
            "current_period_end": None,
            "past_due_since": None,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "configured": bool(settings.stripe_secret_key and settings.stripe_price_pro),
        }
    return {
        "id": subscription.id,
        "plan": subscription.plan,
        "price_eur": subscription.price,
        "status": subscription.status,
        "stripe_price_id": subscription.stripe_price_id,
        "trial_start": subscription.trial_start,
        "trial_end": subscription.trial_end,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "past_due_since": subscription.past_due_since,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "canceled_at": subscription.canceled_at,
        "configured": bool(settings.stripe_secret_key and settings.stripe_price_pro),
    }


def create_checkout_session(
    db: Session,
    *,
    organization_id: int,
    customer_email: str,
) -> str:
    _require_stripe()
    price_id = settings.stripe_price_pro
    if not price_id.startswith("price_"):
        raise HTTPException(
            400,
            detail={
                "code": "stripe_price_invalid",
                "message": (
                    "STRIPE_PRICE_PRO doit être un ID de prix Stripe (price_...), "
                    "pas un ID de produit (prod_...)"
                ),
                "value_prefix": price_id[:5],
            },
        )
    current = _subscription_for_org(db, organization_id)
    if current and current.status in {"active", "trialing"}:
        raise HTTPException(
            409,
            detail={
                "code": "subscription_already_active",
                "message": "Cette organisation possède déjà un abonnement actif",
            },
        )
    metadata = {"organization_id": str(organization_id), "plan": "pro"}
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "payment_method_collection": "always",
        "subscription_data": {
            "trial_period_days": settings.stripe_trial_days,
            "metadata": metadata,
        },
        "metadata": metadata,
        "success_url": f"{settings.frontend_url.rstrip('/')}/abonnement?checkout=success",
        "cancel_url": f"{settings.frontend_url.rstrip('/')}/abonnement?checkout=cancel",
    }
    if current and current.stripe_customer_id:
        params["customer"] = current.stripe_customer_id
    else:
        params["customer_email"] = customer_email
    try:
        session = stripe.checkout.Session.create(**params)
    except stripe.StripeError as exc:
        raise HTTPException(
            502,
            detail={
                "code": "stripe_checkout_failed",
                "message": _stripe_error_message(exc),
            },
        ) from exc
    if not session.url:
        raise HTTPException(
            502,
            detail={
                "code": "stripe_checkout_url_missing",
                "message": "Stripe n’a pas renvoyé d’URL de paiement",
            },
        )
    return session.url


def create_portal_session(db: Session, *, organization_id: int) -> str:
    _require_stripe()
    current = _subscription_for_org(db, organization_id)
    if not current or not current.stripe_customer_id:
        raise HTTPException(
            409,
            detail={
                "code": "stripe_customer_missing",
                "message": "Aucun compte de facturation Stripe pour cette organisation",
            },
        )
    try:
        session = stripe.billing_portal.Session.create(
            customer=current.stripe_customer_id,
            return_url=f"{settings.frontend_url.rstrip('/')}/abonnement",
        )
    except stripe.StripeError as exc:
        raise HTTPException(
            502,
            detail={
                "code": "stripe_portal_failed",
                "message": _stripe_error_message(exc),
            },
        ) from exc
    if not session.url:
        raise HTTPException(
            502,
            detail={
                "code": "stripe_portal_url_missing",
                "message": "Stripe n’a pas renvoyé d’URL de portail",
            },
        )
    return session.url


def _stripe_error_message(exc: stripe.StripeError) -> str:
    user_message = getattr(exc, "user_message", None) or str(exc) or "Erreur Stripe"
    return user_message[:300]


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.utcfromtimestamp(int(value))


def _organization_id(metadata: Any) -> int | None:
    raw = (metadata or {}).get("organization_id")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _find_subscription(
    db: Session,
    *,
    organization_id: int | None = None,
    stripe_subscription_id: str | None = None,
    stripe_customer_id: str | None = None,
) -> Subscription | None:
    query = db.query(Subscription)
    if stripe_subscription_id:
        row = query.filter(Subscription.stripe_subscription_id == stripe_subscription_id).first()
        if row:
            return row
    if stripe_customer_id:
        row = query.filter(Subscription.stripe_customer_id == stripe_customer_id).first()
        if row:
            return row
    if organization_id is not None:
        return (
            query.filter(Subscription.organization_id == organization_id)
            .order_by(Subscription.id.desc())
            .first()
        )
    return None


def _upsert_checkout(db: Session, session: dict[str, Any]) -> None:
    organization_id = _organization_id(session.get("metadata"))
    if organization_id is None:
        return
    if not db.get(Organization, organization_id):
        raise ValueError("Organisation Stripe introuvable")
    row = _find_subscription(
        db,
        organization_id=organization_id,
        stripe_subscription_id=session.get("subscription"),
        stripe_customer_id=session.get("customer"),
    )
    if row and row.organization_id != organization_id:
        raise ValueError("Session Stripe rattachée à une autre organisation")
    if not row:
        row = Subscription(
            organization_id=organization_id,
            plan="pro",
            status="incomplete",
            price=19.0,
        )
    row.stripe_customer_id = session.get("customer") or row.stripe_customer_id
    row.stripe_subscription_id = session.get("subscription") or row.stripe_subscription_id
    row.stripe_price_id = settings.stripe_price_pro or row.stripe_price_id
    db.add(row)


def _upsert_stripe_subscription(db: Session, obj: dict[str, Any]) -> None:
    organization_id = _organization_id(obj.get("metadata"))
    stripe_subscription_id = obj.get("id")
    stripe_customer_id = obj.get("customer")
    row = _find_subscription(
        db,
        organization_id=organization_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_customer_id=stripe_customer_id,
    )
    if not row:
        if organization_id is None:
            return
        if not db.get(Organization, organization_id):
            raise ValueError("Organisation Stripe introuvable")
        row = Subscription(organization_id=organization_id, plan="pro", price=19.0)
    elif organization_id is not None and row.organization_id != organization_id:
        raise ValueError("Abonnement Stripe rattaché à une autre organisation")

    items = ((obj.get("items") or {}).get("data") or [])
    first_item = items[0] if items else {}
    price = (first_item.get("price") or {}).get("id")
    row.plan = "pro"
    row.price = 19.0
    stripe_status = obj.get("status")
    # Conserver toute nouvelle valeur Stripe, mais l'accès reste fermé par défaut dans deps.py.
    row.status = stripe_status or row.status
    if row.status == "past_due" and row.past_due_since is None:
        row.past_due_since = datetime.utcnow()
    elif row.status != "past_due":
        row.past_due_since = None
    row.stripe_customer_id = stripe_customer_id or row.stripe_customer_id
    row.stripe_subscription_id = stripe_subscription_id or row.stripe_subscription_id
    row.stripe_price_id = price or settings.stripe_price_pro or row.stripe_price_id
    row.trial_start = _timestamp(obj.get("trial_start"))
    row.trial_end = _timestamp(obj.get("trial_end"))
    row.current_period_start = _timestamp(
        obj.get("current_period_start") or first_item.get("current_period_start")
    )
    row.current_period_end = _timestamp(
        obj.get("current_period_end") or first_item.get("current_period_end")
    )
    row.cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
    row.canceled_at = _timestamp(obj.get("canceled_at"))
    if row.status == "canceled" and row.canceled_at is None:
        row.canceled_at = datetime.utcnow()
    row.end_date = row.current_period_end
    db.add(row)
    _sync_organization_plan(db, row)


def _invoice_subscription_id(invoice: dict[str, Any]) -> str | None:
    if invoice.get("subscription"):
        return invoice["subscription"]
    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or {}
    return details.get("subscription")


def _apply_invoice_status(db: Session, invoice: dict[str, Any], status: str) -> None:
    row = _find_subscription(
        db,
        stripe_subscription_id=_invoice_subscription_id(invoice),
        stripe_customer_id=invoice.get("customer"),
    )
    if row:
        if status == "active" and row.status not in {"incomplete", "past_due", "unpaid"}:
            return
        if status == "past_due" and row.status in {
            "canceled",
            "incomplete_expired",
            "paused",
        }:
            return
        row.status = status
        row.past_due_since = datetime.utcnow() if status == "past_due" else None
        db.add(row)
        _sync_organization_plan(db, row)


def _sync_organization_plan(db: Session, subscription: Subscription) -> None:
    organization = db.get(Organization, subscription.organization_id)
    if organization:
        organization.subscription_plan = (
            "pro" if subscription.status in PRO_PLAN_STATUSES else "starter"
        )
        db.add(organization)


def apply_webhook_event(db: Session, event: dict[str, Any]) -> None:
    event_type = event.get("type", "")
    obj = ((event.get("data") or {}).get("object") or {})
    if event_type == "checkout.session.completed":
        _upsert_checkout(db, obj)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        if event_type == "customer.subscription.deleted" and not obj.get("status"):
            obj = dict(obj)
            obj["status"] = "canceled"
        _upsert_stripe_subscription(db, obj)
    elif event_type == "invoice.paid":
        _apply_invoice_status(db, obj, "active")
    elif event_type == "invoice.payment_failed":
        _apply_invoice_status(db, obj, "past_due")
