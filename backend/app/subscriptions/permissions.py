from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models_saas import User
from app.subscriptions.access import get_subscription_access
from app.subscriptions.constants import ERROR_CODES, PLANS, PLAN_COMPTAPILOT_MONTHLY


def get_user_entitlements(
    db: Session,
    organization_id: int,
    *,
    user: User | None = None,
) -> dict[str, Any]:
    access = get_subscription_access(db, organization_id, user=user)
    plan = PLANS.get(PLAN_COMPTAPILOT_MONTHLY, {})
    features = dict(plan.get("features") or {})
    if not access.has_access:
        features = {key: False for key in features}
    return {
        "has_access": access.has_access,
        "read_only": access.read_only,
        "plan_code": access.plan_code,
        "subscription_status": access.subscription_status,
        "features": features,
        "limits": plan.get("limits") or {},
        "feature_labels": plan.get("feature_labels") or [],
    }


def can_access_feature(
    db: Session,
    organization_id: int,
    feature_code: str,
    *,
    user: User | None = None,
) -> bool:
    entitlements = get_user_entitlements(db, organization_id, user=user)
    if not entitlements["has_access"]:
        return False
    if entitlements["read_only"] and feature_code.endswith("_write"):
        return False
    return bool(entitlements["features"].get(feature_code, entitlements["has_access"]))


def subscription_error(code: str, *, status: str | None = None, action: str | None = None) -> dict:
    payload: dict[str, Any] = {
        "error": code,
        "message": ERROR_CODES.get(code, "Accès abonnement refusé"),
    }
    if status:
        payload["subscriptionStatus"] = status
    if action:
        payload["action"] = action
    return payload
