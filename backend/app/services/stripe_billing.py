from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import stripe
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Organization, Subscription

logger = logging.getLogger(__name__)

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
                "message": "Paiement sécurisé indisponible pour le moment",
            },
        )
    stripe.api_key = settings.stripe_secret_key


def construct_webhook_event(payload: bytes, signature: str | None) -> dict[str, Any]:
    _require_stripe(webhook=True)
    if not signature:
        raise HTTPException(
            400,
            detail={"code": "stripe_signature_missing", "message": "Signature de requête absente"},
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
            detail={"code": "stripe_signature_invalid", "message": "Signature de requête invalide"},
        ) from exc


def _subscription_for_org(db: Session, organization_id: int) -> Subscription | None:
    rows = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .all()
    )
    if not rows:
        return None
    for status in ("trialing", "active", "past_due", "unpaid", "paused"):
        for row in rows:
            if row.status == status:
                return row
    for row in rows:
        if row.stripe_subscription_id:
            return row
    return rows[0]


def get_organization_subscription(db: Session, organization_id: int) -> Subscription | None:
    return _subscription_for_org(db, organization_id)


def serialize_subscription(
    subscription: Subscription | None,
    *,
    platform_bypass: bool = False,
    db: Session | None = None,
    organization_id: int | None = None,
    user=None,
) -> dict[str, Any]:
    """Sérialisation enrichie via get_subscription_access lorsque possible."""
    if db is not None and organization_id is not None:
        from app.subscriptions.access import get_subscription_access, serialize_access

        access = get_subscription_access(db, organization_id, user=user)
        payload = serialize_access(access)
        if subscription and subscription.stripe_price_id:
            payload["stripe_price_id"] = subscription.stripe_price_id
        if subscription and subscription.past_due_since:
            payload["past_due_since"] = subscription.past_due_since
        # Compat : si bypass forcé (tests) aligner
        if platform_bypass:
            payload["platform_bypass"] = True
            payload["access_granted"] = True
            payload["status"] = "active"
        return payload

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
            "trial_used": False,
            "trial_eligibility_status": "eligible",
        }
    status = subscription.status
    access_granted = platform_bypass or status in ACCESS_STATUSES
    if getattr(subscription, "admin_revoked_at", None):
        access_granted = platform_bypass
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
        "trial_used": bool(getattr(subscription, "trial_used", False)),
        "trial_eligibility_status": getattr(subscription, "trial_eligibility_status", "eligible"),
        "admin_revoked": bool(getattr(subscription, "admin_revoked_at", None)),
    }


def create_checkout_session(
    db: Session,
    *,
    organization_id: int,
    customer_email: str,
    trial_period_days: int | None = None,
) -> tuple[str, str]:
    """Crée une session Checkout. Retourne (url, session_id)."""
    _require_stripe()
    from app.subscriptions.consent import assert_trial_eligible, trial_days_for_checkout

    price_id = settings.stripe_price_pro
    if not price_id.startswith("price_"):
        logger.error("Invalid billing price id configured (prefix=%s)", price_id[:5])
        raise HTTPException(
            503,
            detail={
                "code": "stripe_price_invalid",
                "message": "Paiement sécurisé indisponible pour le moment",
            },
        )
    current = assert_trial_eligible(db, organization_id)
    metadata = {"organization_id": str(organization_id), "plan": "pro"}
    trial_days = trial_days_for_checkout(current) if trial_period_days is None else trial_period_days

    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "payment_method_collection": "always",
        "client_reference_id": str(organization_id),
        "subscription_data": {
            "metadata": metadata,
        },
        "metadata": metadata,
        "success_url": (
            f"{settings.frontend_url.rstrip('/')}/abonnement"
            "?checkout=success&session_id={CHECKOUT_SESSION_ID}"
        ),
        "cancel_url": f"{settings.frontend_url.rstrip('/')}/abonnement?checkout=cancel",
    }
    if trial_days and trial_days > 0:
        params["subscription_data"]["trial_period_days"] = trial_days
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
                "message": "Impossible d’ouvrir le paiement sécurisé",
            },
        )
    session_id = getattr(session, "id", None) or ""
    if current is not None:
        current.stripe_checkout_session_id = session_id or current.stripe_checkout_session_id
        if current.status in {"", "none", None} or current.status == "canceled":
            current.status = "incomplete"
        db.add(current)
        db.flush()
    elif session_id:
        row = Subscription(
            organization_id=organization_id,
            plan="pro",
            status="incomplete",
            price=19.0,
            stripe_checkout_session_id=session_id,
        )
        db.add(row)
        db.flush()
    return session.url, session_id


def create_portal_session(db: Session, *, organization_id: int) -> str:
    _require_stripe()
    current = _subscription_for_org(db, organization_id)
    if not current or not current.stripe_customer_id:
        raise HTTPException(
            409,
            detail={
                "code": "stripe_customer_missing",
                "message": "Aucun moyen de paiement enregistré pour cette organisation",
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
                "message": "Impossible d’ouvrir l’espace facturation",
            },
        )
    return session.url


def _stripe_error_message(exc: stripe.StripeError) -> str:
    raw = getattr(exc, "user_message", None) or str(exc) or ""
    if raw and not any(
        token in raw.lower()
        for token in ("stripe", "api_key", "webhook", "price_", "sk_", "pk_")
    ):
        return raw[:300]
    return "Le service de paiement est temporairement indisponible"


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
    """Résout une ligne existante sans jamais créer de doublon sur les IDs Stripe."""
    db.flush()
    by_sub = None
    by_customer = None
    by_org = None
    if stripe_subscription_id:
        by_sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_subscription_id)
            .first()
        )
    if stripe_customer_id:
        by_customer = (
            db.query(Subscription)
            .filter(Subscription.stripe_customer_id == stripe_customer_id)
            .first()
        )
    if organization_id is not None:
        by_org = (
            db.query(Subscription)
            .filter(Subscription.organization_id == organization_id)
            .order_by(Subscription.id.desc())
            .first()
        )

    # Priorité stricte : ID abonnement Stripe > client Stripe > org.
    chosen = by_sub or by_customer or by_org
    if not chosen:
        return None

    # Nettoie les orphelins incomplets de la même org pour éviter les UNIQUE INSERT.
    if organization_id is not None and (by_sub or by_customer):
        orphans = (
            db.query(Subscription)
            .filter(
                Subscription.organization_id == organization_id,
                Subscription.id != chosen.id,
            )
            .all()
        )
        for orphan in orphans:
            same_sub = (
                stripe_subscription_id
                and orphan.stripe_subscription_id == stripe_subscription_id
            )
            same_customer = (
                stripe_customer_id and orphan.stripe_customer_id == stripe_customer_id
            )
            empty_stripe = not orphan.stripe_subscription_id and not orphan.stripe_customer_id
            incomplete = orphan.status in {"incomplete", "none", ""}
            if same_sub or (incomplete and (empty_stripe or same_customer)):
                db.delete(orphan)
        db.flush()
    return chosen


def _resolve_or_create_subscription(
    db: Session,
    *,
    organization_id: int,
    stripe_subscription_id: str | None = None,
    stripe_customer_id: str | None = None,
) -> Subscription:
    row = _find_subscription(
        db,
        organization_id=organization_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_customer_id=stripe_customer_id,
    )
    if row and row.organization_id != organization_id:
        raise ValueError("Abonnement Stripe rattaché à une autre organisation")
    if row:
        return row
    return Subscription(
        organization_id=organization_id,
        plan="pro",
        status="incomplete",
        price=19.0,
    )


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
    if organization_id is None:
        # Dernier recours : rattacher via une ligne déjà connue.
        existing = _find_subscription(
            db,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
        )
        if existing:
            organization_id = existing.organization_id
        else:
            return
    if not db.get(Organization, organization_id):
        raise ValueError("Organisation Stripe introuvable")

    row = _resolve_or_create_subscription(
        db,
        organization_id=organization_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_customer_id=stripe_customer_id,
    )

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
    # Ne jamais réassigner un ID Stripe déjà porté par une autre ligne.
    if stripe_customer_id:
        conflict = (
            db.query(Subscription)
            .filter(
                Subscription.stripe_customer_id == stripe_customer_id,
                Subscription.id != getattr(row, "id", None),
            )
            .first()
        )
        if conflict is None:
            row.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        conflict = (
            db.query(Subscription)
            .filter(
                Subscription.stripe_subscription_id == stripe_subscription_id,
                Subscription.id != getattr(row, "id", None),
            )
            .first()
        )
        if conflict is None:
            row.stripe_subscription_id = stripe_subscription_id
        elif conflict.id != row.id:
            # Fusionner vers la ligne qui possède déjà l’ID Stripe.
            if row.id is None:
                db.expunge(row)
            else:
                db.delete(row)
                db.flush()
            row = conflict
            row.organization_id = organization_id
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
    if row.cancel_at_period_end and row.cancel_requested_at is None:
        row.cancel_requested_at = datetime.utcnow()
    if not row.cancel_at_period_end:
        row.cancel_requested_at = None
    if row.status == "canceled" and row.canceled_at is None:
        row.canceled_at = datetime.utcnow()
    row.access_ends_at = row.current_period_end if row.cancel_at_period_end else row.access_ends_at
    if row.status == "trialing" and not row.trial_used:
        row.trial_used = True
        row.trial_used_at = row.trial_start or datetime.utcnow()
        row.trial_source_subscription_id = stripe_subscription_id
        if row.trial_eligibility_status != "admin_granted":
            row.trial_eligibility_status = "already_used"
    if row.status == "past_due":
        row.payment_failure_count = int(row.payment_failure_count or 0) + 0  # conservé; incrément invoice
    product = price_obj.get("product")
    if isinstance(product, str):
        row.stripe_product_id = product
    elif isinstance(product, dict) and product.get("id"):
        row.stripe_product_id = str(product["id"])
    row.end_date = row.current_period_end
    db.add(row)
    db.flush()
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
    row = _resolve_or_create_subscription(
        db,
        organization_id=organization_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if customer_id:
        conflict = (
            db.query(Subscription)
            .filter(
                Subscription.stripe_customer_id == customer_id,
                Subscription.id != getattr(row, "id", None),
            )
            .first()
        )
        if conflict is None:
            row.stripe_customer_id = customer_id
        elif conflict.organization_id == organization_id:
            if row.id is None:
                db.expunge(row)
            elif row.id != conflict.id:
                db.delete(row)
                db.flush()
            row = conflict
    if subscription_id:
        conflict = (
            db.query(Subscription)
            .filter(
                Subscription.stripe_subscription_id == subscription_id,
                Subscription.id != getattr(row, "id", None),
            )
            .first()
        )
        if conflict is None:
            row.stripe_subscription_id = subscription_id
        elif conflict.organization_id == organization_id:
            if row.id is None:
                db.expunge(row)
            elif row.id != conflict.id:
                db.delete(row)
                db.flush()
            row = conflict
            row.stripe_subscription_id = subscription_id
        else:
            raise ValueError("Session Stripe rattachée à une autre organisation")
    row.stripe_price_id = settings.stripe_price_pro or row.stripe_price_id
    session_id = _stripe_id(session.get("id"))
    if session_id:
        row.stripe_checkout_session_id = session_id
    if row.status in {"", "none"} or not row.status:
        row.status = "incomplete"
    db.add(row)
    db.flush()

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
                    "message": "Cette session de paiement ne correspond pas à l’organisation active",
                },
            )
        try:
            _upsert_checkout(db, session_data)
            db.commit()
        except IntegrityError:
            db.rollback()
            try:
                _upsert_checkout(db, session_data)
                db.commit()
            except Exception as exc:
                db.rollback()
                raise HTTPException(
                    502,
                    detail={
                        "code": "stripe_checkout_sync_failed",
                        "message": "Impossible d’enregistrer la session de paiement. Réessayez.",
                    },
                ) from exc
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                502,
                detail={
                    "code": "stripe_checkout_sync_failed",
                    "message": "Impossible d’enregistrer la session de paiement. Réessayez.",
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
    subscription_id = _invoice_subscription_id(invoice)
    if not subscription_id:
        return
    row = _find_subscription(db, stripe_subscription_id=subscription_id)
    if not row:
        return
    if row.status in {"canceled", "incomplete_expired", "paused"}:
        return
    if status == "past_due":
        row.status = "past_due"
        row.past_due_since = row.past_due_since or datetime.utcnow()
        row.payment_failure_count = int(row.payment_failure_count or 0) + 1
        row.last_payment_failure_at = datetime.utcnow()
    elif status == "active":
        if row.status == "trialing":
            # Ne pas écraser un essai encore en cours
            row.last_payment_succeeded_at = datetime.utcnow()
        else:
            row.status = "active"
            row.past_due_since = None
            row.last_payment_succeeded_at = datetime.utcnow()
    else:
        row.status = status
        row.past_due_since = datetime.utcnow() if status == "past_due" else None
    db.add(row)
    _sync_organization_plan(db, row)


def sync_subscription_from_stripe(db: Session, stripe_subscription_id: str) -> Subscription | None:
    """Source de vérité Stripe pour un abonnement donné."""
    _require_stripe()
    try:
        obj = stripe.Subscription.retrieve(stripe_subscription_id)
    except stripe.StripeError as exc:
        raise HTTPException(
            502,
            detail={
                "code": "STRIPE_SUBSCRIPTION_NOT_FOUND",
                "message": _stripe_error_message(exc),
            },
        ) from exc
    data = _as_dict(obj)
    _upsert_stripe_subscription(db, data)
    db.flush()
    return _find_subscription(db, stripe_subscription_id=stripe_subscription_id)


def apply_webhook_event(db: Session, event: dict[str, Any]) -> None:
    event_type = event.get("type", "")
    obj = ((event.get("data") or {}).get("object") or {})
    if event_type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        _upsert_checkout(db, obj)
    elif event_type == "checkout.session.async_payment_failed":
        organization_id = _organization_id(_meta_dict(obj.get("metadata")))
        if organization_id:
            row = _subscription_for_org(db, organization_id)
            if row and row.status == "incomplete":
                row.status = "incomplete_expired"
                db.add(row)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.trial_will_end",
    }:
        if event_type == "customer.subscription.deleted" and not obj.get("status"):
            obj = dict(obj)
            obj["status"] = "canceled"
        _upsert_stripe_subscription(db, obj)
        if event_type == "customer.subscription.trial_will_end":
            from app.subscriptions.notifications import notify_org_owners

            row = _find_subscription(db, stripe_subscription_id=_stripe_id(obj.get("id")))
            if row:
                notify_org_owners(
                    db,
                    organization_id=row.organization_id,
                    notification_type="trial_ending",
                    subscription=row,
                    suffix=f"stripe_trial_will_end:{row.stripe_subscription_id}",
                    template_kwargs={
                        "trial_end": row.trial_end.isoformat() if row.trial_end else None
                    },
                )
    elif event_type in {"invoice.paid", "invoice.payment_succeeded"}:
        _apply_invoice_status(db, obj, "active")
    elif event_type in {"invoice.payment_failed", "invoice.payment_action_required"}:
        _apply_invoice_status(db, obj, "past_due")
        row = _find_subscription(db, stripe_subscription_id=_invoice_subscription_id(obj))
        if row:
            from app.subscriptions.notifications import notify_org_owners

            notify_org_owners(
                db,
                organization_id=row.organization_id,
                notification_type="payment_failed",
                subscription=row,
                suffix=f"invoice:{obj.get('id')}",
                template_kwargs={
                    "grace_until": (
                        (row.past_due_since.isoformat() if row.past_due_since else None)
                    )
                },
            )
    elif event_type in {"invoice.created", "invoice.finalized", "payment_method.attached", "customer.updated"}:
        # Événements journalisés sans mutation critique
        return
    else:
        return
