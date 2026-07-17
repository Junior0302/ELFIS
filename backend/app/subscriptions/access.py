from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models_saas import Subscription, User
from app.subscriptions.constants import (
    ACCESS_RAW_STATUSES,
    PLAN_COMPTAPILOT_MONTHLY,
    PRICE_AMOUNT_CENTS,
    UX_STATUS_LABELS,
)


@dataclass
class SubscriptionAccess:
    organization_id: int
    account_status: str
    subscription_status: str
    raw_status: str
    plan_code: str
    has_access: bool
    read_only: bool
    is_trial: bool
    trial_started_at: datetime | None
    trial_ends_at: datetime | None
    current_period_starts_at: datetime | None
    current_period_ends_at: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    access_ends_at: datetime | None
    next_billing_at: datetime | None
    next_billing_amount: int | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    access_reason: str
    platform_bypass: bool
    trial_eligibility_status: str
    trial_used: bool
    grace_until: datetime | None
    admin_revoked: bool
    admin_revoked_reason_public: str
    label: str
    configured: bool
    price_eur: float
    subscription_id: int | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, datetime):
                data[key] = value.isoformat() + "Z" if value.tzinfo is None else value.isoformat()
        return data


def _platform_bypass(user: User | None) -> bool:
    if not user or user.status != "active":
        return False
    if user.is_platform_admin:
        return True
    return user.email.lower() in settings.platform_admin_email_set


def _latest_subscription(db: Session, organization_id: int) -> Subscription | None:
    rows = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .all()
    )
    if not rows:
        return None
    for status in ("trialing", "active", "past_due", "unpaid", "paused", "incomplete"):
        for row in rows:
            if row.status == status:
                return row
    for row in rows:
        if row.stripe_subscription_id:
            return row
    return rows[0]


def get_subscription_access(
    db: Session,
    organization_id: int,
    *,
    user: User | None = None,
    now: datetime | None = None,
) -> SubscriptionAccess:
    now = now or datetime.utcnow()
    bypass = _platform_bypass(user)
    configured = bool(settings.stripe_secret_key and settings.stripe_price_pro)
    row = _latest_subscription(db, organization_id)

    if bypass:
        return SubscriptionAccess(
            organization_id=organization_id,
            account_status="active",
            subscription_status="active",
            raw_status=row.status if row else "none",
            plan_code="elfadmin",
            has_access=True,
            read_only=False,
            is_trial=False,
            trial_started_at=None,
            trial_ends_at=None,
            current_period_starts_at=None,
            current_period_ends_at=None,
            cancel_at_period_end=False,
            canceled_at=None,
            access_ends_at=None,
            next_billing_at=None,
            next_billing_amount=None,
            stripe_customer_id=row.stripe_customer_id if row else None,
            stripe_subscription_id=row.stripe_subscription_id if row else None,
            access_reason="platform_admin_bypass",
            platform_bypass=True,
            trial_eligibility_status="blocked",
            trial_used=bool(row.trial_used) if row else False,
            grace_until=None,
            admin_revoked=False,
            admin_revoked_reason_public="",
            label="Accès administrateur ELFIS",
            configured=configured,
            price_eur=0,
            subscription_id=row.id if row else None,
        )

    if not row:
        return SubscriptionAccess(
            organization_id=organization_id,
            account_status="active",
            subscription_status="none",
            raw_status="none",
            plan_code="free",
            has_access=False,
            read_only=False,
            is_trial=False,
            trial_started_at=None,
            trial_ends_at=None,
            current_period_starts_at=None,
            current_period_ends_at=None,
            cancel_at_period_end=False,
            canceled_at=None,
            access_ends_at=None,
            next_billing_at=None,
            next_billing_amount=PRICE_AMOUNT_CENTS,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            access_reason="no_subscription",
            platform_bypass=False,
            trial_eligibility_status="eligible",
            trial_used=False,
            grace_until=None,
            admin_revoked=False,
            admin_revoked_reason_public="",
            label=UX_STATUS_LABELS["none"],
            configured=configured,
            price_eur=19.0,
            subscription_id=None,
        )

    raw = row.status or "none"
    admin_revoked = bool(row.admin_revoked_at)
    grace_until = None
    read_only = False
    has_access = False
    access_reason = f"status:{raw}"

    if admin_revoked:
        ux_status = "admin_revoked"
        access_reason = "admin_revoked"
    elif raw in {"incomplete", "incomplete_expired"}:
        ux_status = "checkout_pending" if raw == "incomplete" else "incomplete_expired"
        access_reason = "checkout_pending"
    elif raw in ACCESS_RAW_STATUSES and row.cancel_at_period_end:
        ux_status = "cancel_scheduled"
        has_access = True
        access_reason = "cancel_at_period_end_access_until_period_end"
    elif raw in ACCESS_RAW_STATUSES:
        ux_status = raw
        has_access = True
        access_reason = f"stripe_{raw}"
    elif raw == "past_due":
        grace_until = (
            row.past_due_since + timedelta(days=settings.stripe_past_due_grace_days)
            if row.past_due_since
            else None
        )
        if grace_until and now <= grace_until:
            has_access = True
            read_only = True
            access_reason = "past_due_grace_read_only"
        else:
            access_reason = "past_due_grace_expired"
        ux_status = "past_due"
    else:
        ux_status = raw if raw in UX_STATUS_LABELS else "canceled"
        access_reason = f"inactive:{raw}"

    access_ends = row.access_ends_at
    if row.cancel_at_period_end and row.current_period_end:
        access_ends = row.current_period_end
    elif raw in {"canceled", "expired"}:
        access_ends = row.canceled_at or row.current_period_end or row.end_date

    next_billing = None
    next_amount = None
    if has_access and not row.cancel_at_period_end and not admin_revoked:
        next_billing = row.current_period_end if raw == "active" else row.trial_end
        next_amount = PRICE_AMOUNT_CENTS

    eligibility = row.trial_eligibility_status or "eligible"
    if row.trial_used and eligibility == "eligible":
        eligibility = "already_used"

    return SubscriptionAccess(
        organization_id=organization_id,
        account_status="active",
        subscription_status=ux_status,
        raw_status=raw,
        plan_code=PLAN_COMPTAPILOT_MONTHLY if row.plan in {"pro", PLAN_COMPTAPILOT_MONTHLY} else row.plan,
        has_access=has_access and not admin_revoked,
        read_only=read_only,
        is_trial=raw == "trialing",
        trial_started_at=row.trial_start,
        trial_ends_at=row.trial_end,
        current_period_starts_at=row.current_period_start,
        current_period_ends_at=row.current_period_end,
        cancel_at_period_end=bool(row.cancel_at_period_end),
        canceled_at=row.canceled_at,
        access_ends_at=access_ends,
        next_billing_at=next_billing,
        next_billing_amount=next_amount,
        stripe_customer_id=row.stripe_customer_id,
        stripe_subscription_id=row.stripe_subscription_id,
        access_reason=access_reason,
        platform_bypass=False,
        trial_eligibility_status=eligibility,
        trial_used=bool(row.trial_used),
        grace_until=grace_until,
        admin_revoked=admin_revoked,
        admin_revoked_reason_public=row.admin_revoked_reason_public or "",
        label=UX_STATUS_LABELS.get(ux_status, ux_status),
        configured=configured,
        price_eur=float(row.price or 19),
        subscription_id=row.id,
    )


def serialize_access(access: SubscriptionAccess) -> dict[str, Any]:
    """Payload compatible API front (SubscriptionInfo enrichi)."""
    base = access.to_dict()
    return {
        "id": access.subscription_id,
        "plan": "elfadmin" if access.platform_bypass else ("pro" if access.plan_code != "free" else "pro"),
        "plan_code": access.plan_code,
        "price_eur": access.price_eur,
        "status": access.subscription_status,
        "raw_status": access.raw_status,
        "stripe_price_id": None,
        "trial_start": base["trial_started_at"],
        "trial_end": base["trial_ends_at"],
        "current_period_start": base["current_period_starts_at"],
        "current_period_end": base["current_period_ends_at"],
        "past_due_since": None,
        "grace_until": base["grace_until"],
        "cancel_at_period_end": access.cancel_at_period_end,
        "canceled_at": base["canceled_at"],
        "access_ends_at": base["access_ends_at"],
        "next_billing_at": base["next_billing_at"],
        "next_billing_amount_cents": access.next_billing_amount,
        "configured": access.configured,
        "platform_bypass": access.platform_bypass,
        "access_granted": access.has_access,
        "read_only": access.read_only,
        "is_trial": access.is_trial,
        "access_reason": access.access_reason,
        "label": access.label,
        "trial_used": access.trial_used,
        "trial_eligibility_status": access.trial_eligibility_status,
        "admin_revoked": access.admin_revoked,
        "admin_revoked_reason_public": access.admin_revoked_reason_public,
        "stripe_customer_id": access.stripe_customer_id,
        "stripe_subscription_id": access.stripe_subscription_id,
    }
