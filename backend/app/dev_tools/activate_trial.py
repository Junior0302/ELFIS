"""Activation d'essai locale — développement / test uniquement (C1.2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.billing.subscription_service import SubscriptionService
from app.config import settings
from app.models_saas import Organization, Subscription
from app.security.security_config import environment_name
from app.services.auth import write_audit
from app.subscriptions.access import get_subscription_access, serialize_access

logger = logging.getLogger(__name__)

Outcome = Literal["created", "already_active"]

_ALLOWED_ENVIRONMENTS = frozenset({"development", "test"})
_ACCESS_STATUSES = frozenset({"trialing", "active"})


@dataclass(frozen=True)
class ActivateTrialResult:
    outcome: Outcome
    subscription: dict[str, Any]
    environment: str


def _trial_days() -> int:
    return int(getattr(settings, "elfis_trial_days", None) or settings.stripe_trial_days or 14)


def assert_developer_trial_environment() -> str:
    """Liste blanche stricte + flag ELFIS_DEV_TRIAL_ENABLED."""
    caps = resolve_developer_trial_capabilities()
    if not caps["environment_allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "dev_trial_environment_forbidden",
                "message": (
                    "L’activation d’essai développeur est limitée aux environnements "
                    "development et test."
                ),
                "environment": caps["environment"],
            },
        )
    if not caps["flag_enabled"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "dev_trial_disabled",
                "message": (
                    "Activation d’essai développeur désactivée. "
                    "Définir ELFIS_DEV_TRIAL_ENABLED=true (développement uniquement)."
                ),
                "environment": caps["environment"],
            },
        )
    return str(caps["environment"])


def resolve_developer_trial_capabilities() -> dict[str, Any]:
    """État backend de l’essai local (sans side-effect)."""
    env = environment_name()
    environment_allowed = env in _ALLOWED_ENVIRONMENTS
    flag_enabled = bool(getattr(settings, "elfis_dev_trial_enabled", False))
    allowed = environment_allowed and flag_enabled
    reason: str | None = None
    if not environment_allowed:
        reason = "dev_trial_environment_forbidden"
    elif not flag_enabled:
        reason = "dev_trial_disabled"
    return {
        "allowed": allowed,
        "environment": env,
        "environment_allowed": environment_allowed,
        "flag_enabled": flag_enabled,
        "reason": reason,
    }


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


def _require_active_organization(db: Session, organization_id: int) -> Organization:
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "organization_not_found",
                "message": "Organisation introuvable",
            },
        )
    platform_status = (getattr(org, "platform_status", None) or "active").strip().lower()
    if platform_status != "active":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "organization_inactive",
                "message": "Organisation inactive : activation d’essai refusee.",
                "platform_status": platform_status,
            },
        )
    return org


def _serialize_payload(access_payload: dict[str, Any], row: Subscription | None) -> dict[str, Any]:
    payload = dict(access_payload)
    if row and row.stripe_price_id:
        payload["stripe_price_id"] = row.stripe_price_id
    if row and row.past_due_since:
        payload["past_due_since"] = row.past_due_since
    return payload


def activate_developer_trial(
    db: Session,
    *,
    user_id: int,
    organization_id: int,
) -> ActivateTrialResult:
    """Crée un véritable essai local (status=trialing) pour l’organisation courante."""
    env = assert_developer_trial_environment()
    _require_active_organization(db, organization_id)

    row = _latest_subscription(db, organization_id)

    if row and row.admin_revoked_at:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "subscription_incompatible",
                "message": (
                    "Abonnement révoqué par la plateforme : "
                    "réactivation développeur impossible."
                ),
                "status": "admin_revoked",
            },
        )

    if row and (row.status or "") in _ACCESS_STATUSES:
        access = get_subscription_access(db, organization_id)
        payload = _serialize_payload(serialize_access(access), row)
        _record_audit(
            db,
            user_id=user_id,
            organization_id=organization_id,
            environment=env,
            outcome="already_active",
            trial_start=row.trial_start,
            trial_end=row.trial_end,
        )
        logger.info(
            "developer_trial_activated",
            extra={
                "event": "developer_trial_activated",
                "outcome": "already_active",
                "user_id": user_id,
                "organization_id": organization_id,
                "environment": env,
                "trial_start": row.trial_start.isoformat() if row.trial_start else None,
                "trial_end": row.trial_end.isoformat() if row.trial_end else None,
            },
        )
        return ActivateTrialResult(
            outcome="already_active",
            subscription=payload,
            environment=env,
        )

    now = datetime.utcnow()
    trial_end = now + timedelta(days=_trial_days())

    if row is None:
        row = Subscription(
            organization_id=organization_id,
            plan="pro",
            status="trialing",
            price=19.0,
        )
        db.add(row)
    else:
        row.plan = row.plan or "pro"
        row.price = float(row.price or 19.0)
        row.status = "trialing"

    row.trial_start = now
    row.trial_end = trial_end
    row.trial_used = False
    row.trial_used_at = None
    row.trial_eligibility_status = "eligible"
    row.current_period_start = now
    row.current_period_end = trial_end
    row.cancel_at_period_end = False
    row.cancel_requested_at = None
    row.canceled_at = None
    row.access_ends_at = trial_end
    row.past_due_since = None
    # Pas de faux IDs Stripe — laisser null si absents.
    db.add(row)

    try:
        db.flush()
        SubscriptionService(db).sync_from_legacy(organization_id, rebuild=True)
        db.flush()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "developer_trial_sync_failed",
            extra={
                "event": "developer_trial_sync_failed",
                "user_id": user_id,
                "organization_id": organization_id,
                "environment": env,
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "dev_trial_sync_failed",
                "message": "Synchronisation de l’abonnement impossible.",
            },
        ) from exc

    access = get_subscription_access(db, organization_id)
    if not access.has_access or access.subscription_status != "trialing":
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "code": "dev_trial_access_inconsistent",
                "message": "L’essai a été écrit mais l’accès produit n’est pas cohérent.",
            },
        )

    payload = _serialize_payload(serialize_access(access), row)
    _record_audit(
        db,
        user_id=user_id,
        organization_id=organization_id,
        environment=env,
        outcome="created",
        trial_start=row.trial_start,
        trial_end=row.trial_end,
    )
    logger.info(
        "developer_trial_activated",
        extra={
            "event": "developer_trial_activated",
            "outcome": "created",
            "user_id": user_id,
            "organization_id": organization_id,
            "environment": env,
            "trial_start": row.trial_start.isoformat() if row.trial_start else None,
            "trial_end": row.trial_end.isoformat() if row.trial_end else None,
        },
    )
    return ActivateTrialResult(outcome="created", subscription=payload, environment=env)


def _record_audit(
    db: Session,
    *,
    user_id: int,
    organization_id: int,
    environment: str,
    outcome: Outcome,
    trial_start: datetime | None,
    trial_end: datetime | None,
) -> None:
    start_s = trial_start.isoformat() if trial_start else ""
    end_s = trial_end.isoformat() if trial_end else ""
    action = (
        f"developer_trial_activated:{outcome}:env={environment}"
        f":start={start_s}:end={end_s}"
    )[:255]
    write_audit(
        db,
        user_id=user_id,
        organization_id=organization_id,
        action=action,
        module="dev_tools",
    )
