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
ACCESS_STATUSES = {"active", "trialing"}


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


def serialize_subscription(
    subscription: Subscription | None,
    *,
    platform_bypass: bool = False,
) -> dict[str, Any]:
    configured = bool(settings.stripe_secret_key and settings.stripe_price_pro)
    if not subscription:
        return {
            "plan": "pro" if not platform_bypass else "elfadmin",
            "price_eur": 0 if platform_bypass else 19,
            "status": "active" if platform_bypass else "none",
            "trial_start": None,
            "trial_end": None,
            "current_period_start": None,
            "current_period_end": None,
            "past_due_since": None,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "configured": configured,
            "platform_bypass": platform_bypass,
            "access_granted": platform_bypass,
        }
    status = subscription.status
    access_granted = platform_bypass or status in ACCESS_STATUSES
    return {
        "id": subscription.id,
        "plan": "elfadmin" if platform_bypass and status == "none" else subscription.plan,
        "price_eur": subscription.price,
        "status": "active" if platform_bypass and status not in ACCESS_STATUSES else status,
        "stripe_price_id": subscription.stripe_price_id,
        "trial_start": subscription.trial_start,
        "trial_end": subscription.trial_end,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "past_due_since": subscription.past_due_since,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "canceled_at": subscription.canceled_at,
        "configured": configured,
        "platform_bypass": platform_bypass,
        "access_granted": access_granted,
        "raw_status": status,
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
    if current and current.status in ACCESS_STATUSES:
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
        "client_reference_id": str(organization_id),
        "subscription_data": {
            "trial_period_days": settings.stripe_trial_days,
            "metadata": metadata,
        },
        "metadata": metadata,
        "success_url": (
            f"{settings.frontend_url.rstrip('/')}/abonnement"
            "?checkout=success&session_id={CHECKOUT_SESSION_ID}"
        ),
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


def _as_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return {str(key): value for key, value in obj.items()}
    if hasattr(obj, "to_dict_recursive"):
        try:
            return obj.to_dict_recursive()  # type: ignore[no-any-return]
        except Exception:
            pass
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict()  # type: ignore[no-any-return]
        except Exception:
            pass
    try:
        return dict(obj)
    except Exception:
        return {}


def _meta_dict(value: Any) -> dict[str, Any]:
    data = _as_dict(value) if value is not None else {}
    return {str(key): data[key] for key in data}


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


def _stripe_id(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        raw = value.get("id")
        return raw if isinstance(raw, str) and raw else None
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


def _sync_organization_plan(db: Session, subscription: Subscription) -> None:
    organization = db.get(Organization, subscription.organization_id)
    if organization:
        organization.subscription_plan = (
            "pro" if subscription.status in PRO_PLAN_STATUSES else "starter"
        )
        db.add(organization)


def _upsert_stripe_subscription(db: Session, obj: dict[str, Any]) -> None:
    organization_id = _organization_id(_meta_dict(obj.get("metadata")))
    stripe_subscription_id = _stripe_id(obj.get("id")) or (
        obj.get("id") if isinstance(obj.get("id"), str) else None
    )
    stripe_customer_id = _stripe_id(obj.get("customer"))
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
    first_item = _as_dict(items[0]) if items else {}
    price_obj = first_item.get("price")
    if not isinstance(price_obj, dict):
        price_obj = _as_dict(price_obj)
    price = price_obj.get("id")
    row.plan = "pro"
    row.price = 19.0
    stripe_status = obj.get("status")
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


def _upsert_checkout(db: Session, session: dict[str, Any]) -> None:
    organization_id = _organization_id(_meta_dict(session.get("metadata")))
    if organization_id is None:
        ref = session.get("client_reference_id")
        try:
            organization_id = int(ref) if ref is not None else None
        except (TypeError, ValueError):
            organization_id = None
    if organization_id is None:
        return
    if not db.get(Organization, organization_id):
        raise ValueError("Organisation Stripe introuvable")

    customer_id = _stripe_id(session.get("customer"))
    subscription_raw = session.get("subscription")
    subscription_id = _stripe_id(subscription_raw)
    row = _find_subscription(
        db,
        organization_id=organization_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
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
    row.stripe_customer_id = customer_id or row.stripe_customer_id
    row.stripe_subscription_id = subscription_id or row.stripe_subscription_id
    row.stripe_price_id = settings.stripe_price_pro or row.stripe_price_id
    db.add(row)

    if isinstance(subscription_raw, dict) and subscription_raw.get("id"):
        sub_data = dict(subscription_raw)
        meta = _meta_dict(sub_data.get("metadata"))
        if not meta.get("organization_id"):
            meta["organization_id"] = str(organization_id)
            meta.setdefault("plan", "pro")
        sub_data["metadata"] = meta
        _upsert_stripe_subscription(db, sub_data)
        return

    if subscription_id and settings.stripe_secret_key:
        try:
            stripe.api_key = settings.stripe_secret_key
            remote = stripe.Subscription.retrieve(subscription_id)
            remote_data = _as_dict(remote)
            meta = _meta_dict(remote_data.get("metadata"))
            if not meta.get("organization_id"):
                meta["organization_id"] = str(organization_id)
                meta.setdefault("plan", "pro")
                remote_data["metadata"] = meta
            _upsert_stripe_subscription(db, remote_data)
        except stripe.StripeError:
            pass


def _recover_from_recent_checkout_sessions(
    db: Session,
    organization_id: int,
) -> Subscription | None:
    try:
        listed = stripe.checkout.Session.list(limit=40)
    except stripe.StripeError as exc:
        raise HTTPException(
            502,
            detail={
                "code": "stripe_session_list_failed",
                "message": _stripe_error_message(exc),
            },
        ) from exc

    for item in listed.data or []:
        data = _as_dict(item)
        meta_org = _organization_id(_meta_dict(data.get("metadata")))
        ref = data.get("client_reference_id")
        try:
            ref_org = int(ref) if ref is not None else None
        except (TypeError, ValueError):
            ref_org = None
        if meta_org != organization_id and ref_org != organization_id:
            continue
        if data.get("status") != "complete":
            continue
        try:
            _upsert_checkout(db, data)
            db.commit()
        except Exception:
            db.rollback()
            continue
        row = _subscription_for_org(db, organization_id)
        if row and row.status in ACCESS_STATUSES:
            return row
        if row and row.stripe_subscription_id:
            try:
                remote = stripe.Subscription.retrieve(row.stripe_subscription_id)
                remote_data = _as_dict(remote)
                meta = _meta_dict(remote_data.get("metadata"))
                if not meta.get("organization_id"):
                    meta["organization_id"] = str(organization_id)
                    meta.setdefault("plan", "pro")
                    remote_data["metadata"] = meta
                _upsert_stripe_subscription(db, remote_data)
                db.commit()
            except Exception:
                db.rollback()
            return _subscription_for_org(db, organization_id)
        if row:
            return row
    return _subscription_for_org(db, organization_id)


def sync_checkout_session(
    db: Session,
    *,
    organization_id: int,
    session_id: str | None = None,
) -> Subscription | None:
    """Resynchronise l'abonnement depuis Stripe (retour checkout ou rattrapage webhook)."""
    _require_stripe()
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(
                session_id,
                expand=["subscription"],
            )
        except stripe.StripeError as exc:
            raise HTTPException(
                502,
                detail={
                    "code": "stripe_session_retrieve_failed",
                    "message": _stripe_error_message(exc),
                },
            ) from exc
        session_data = _as_dict(session)
        meta_org = _organization_id(_meta_dict(session_data.get("metadata")))
        ref = session_data.get("client_reference_id")
        try:
            ref_org = int(ref) if ref is not None else None
        except (TypeError, ValueError):
            ref_org = None
        linked_org = meta_org if meta_org is not None else ref_org
        if linked_org is not None and linked_org != organization_id:
            raise HTTPException(
                403,
                detail={
                    "code": "stripe_session_org_mismatch",
                    "message": "Cette session Stripe ne correspond pas à l’organisation active",
                },
            )
        try:
            _upsert_checkout(db, session_data)
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                502,
                detail={
                    "code": "stripe_checkout_sync_failed",
                    "message": f"Impossible d’enregistrer la session Stripe : {str(exc)[:180]}",
                },
            ) from exc
        row = _subscription_for_org(db, organization_id)
        if row and row.status in ACCESS_STATUSES:
            return row

    row = _subscription_for_org(db, organization_id)
    if row and row.stripe_subscription_id:
        try:
            remote = stripe.Subscription.retrieve(row.stripe_subscription_id)
            remote_data = _as_dict(remote)
            meta = _meta_dict(remote_data.get("metadata"))
            if not meta.get("organization_id"):
                meta["organization_id"] = str(organization_id)
                meta.setdefault("plan", "pro")
                remote_data["metadata"] = meta
            _upsert_stripe_subscription(db, remote_data)
            db.commit()
        except stripe.StripeError as exc:
            raise HTTPException(
                502,
                detail={
                    "code": "stripe_subscription_retrieve_failed",
                    "message": _stripe_error_message(exc),
                },
            ) from exc
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                502,
                detail={
                    "code": "stripe_subscription_sync_failed",
                    "message": f"Impossible de synchroniser l’abonnement : {str(exc)[:180]}",
                },
            ) from exc
        row = _subscription_for_org(db, organization_id)
        if row and row.status in ACCESS_STATUSES:
            return row

    if row and row.stripe_customer_id:
        try:
            listed = stripe.Subscription.list(
                customer=row.stripe_customer_id,
                status="all",
                limit=5,
            )
        except stripe.StripeError as exc:
            raise HTTPException(
                502,
                detail={
                    "code": "stripe_subscription_list_failed",
                    "message": _stripe_error_message(exc),
                },
            ) from exc
        data = list(listed.data or [])
        if data:
            preferred = next(
                (item for item in data if getattr(item, "status", None) in ACCESS_STATUSES),
                data[0],
            )
            preferred_data = _as_dict(preferred)
            meta = _meta_dict(preferred_data.get("metadata"))
            if not meta.get("organization_id"):
                meta["organization_id"] = str(organization_id)
                meta.setdefault("plan", "pro")
                preferred_data["metadata"] = meta
            try:
                _upsert_stripe_subscription(db, preferred_data)
                db.commit()
            except Exception as exc:
                db.rollback()
                raise HTTPException(
                    502,
                    detail={
                        "code": "stripe_subscription_sync_failed",
                        "message": f"Impossible de synchroniser l’abonnement : {str(exc)[:180]}",
                    },
                ) from exc
            row = _subscription_for_org(db, organization_id)
            if row and row.status in ACCESS_STATUSES:
                return row

    return _recover_from_recent_checkout_sessions(db, organization_id)


def _invoice_subscription_id(invoice: dict[str, Any]) -> str | None:
    direct = _stripe_id(invoice.get("subscription"))
    if direct:
        return direct
    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or {}
    return _stripe_id(details.get("subscription"))


def _apply_invoice_status(db: Session, invoice: dict[str, Any], status: str) -> None:
    row = _find_subscription(
        db,
        stripe_subscription_id=_invoice_subscription_id(invoice),
        stripe_customer_id=_stripe_id(invoice.get("customer")),
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
