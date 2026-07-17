from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models_saas import Subscription
from app.services.auth import write_audit


def admin_revoke_access(
    db: Session,
    *,
    subscription: Subscription,
    admin_user_id: int,
    reason_public: str,
    reason_internal: str = "",
) -> Subscription:
    subscription.admin_revoked_at = datetime.utcnow()
    subscription.admin_revoked_by = admin_user_id
    subscription.admin_revoked_reason_public = (reason_public or "").strip()[:2000]
    subscription.admin_revoked_reason_internal = (reason_internal or "").strip()[:4000]
    db.add(subscription)
    write_audit(
        db,
        user_id=admin_user_id,
        organization_id=subscription.organization_id,
        action=f"admin_revoke_subscription:{subscription.id}",
        module="subscriptions",
    )
    return subscription


def admin_restore_access(
    db: Session,
    *,
    subscription: Subscription,
    admin_user_id: int,
    reason: str = "",
) -> Subscription:
    subscription.admin_revoked_at = None
    subscription.admin_revoked_by = None
    subscription.admin_revoked_reason_public = ""
    subscription.admin_revoked_reason_internal = reason or ""
    db.add(subscription)
    write_audit(
        db,
        user_id=admin_user_id,
        organization_id=subscription.organization_id,
        action=f"admin_restore_subscription:{subscription.id}",
        module="subscriptions",
    )
    return subscription


def admin_grant_trial(
    db: Session,
    *,
    subscription: Subscription | None,
    organization_id: int,
    admin_user_id: int,
    reason: str,
) -> Subscription:
    if subscription is None:
        subscription = Subscription(
            organization_id=organization_id,
            plan="pro",
            status="none",
            price=19.0,
        )
        db.add(subscription)
        db.flush()
    subscription.trial_used = False
    subscription.trial_eligibility_status = "admin_granted"
    subscription.trial_used_at = None
    db.add(subscription)
    write_audit(
        db,
        user_id=admin_user_id,
        organization_id=organization_id,
        action=f"admin_grant_trial:{subscription.id}:{reason[:120]}",
        module="subscriptions",
    )
    return subscription
