"""Routes développeur — activation d'essai locale (C1.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.dev_tools.activate_trial import (
    activate_developer_trial,
    resolve_developer_trial_capabilities,
)
from app.subscriptions.access import get_subscription_access

router = APIRouter(prefix="/dev", tags=["dev-tools"])


@router.get("/trial-status")
def trial_status(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Indique si l’essai local est autorisé par le backend (sans l’activer)."""
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")

    caps = resolve_developer_trial_capabilities()
    organization_id = auth.organization_id
    already_active = False
    if organization_id is not None:
        access = get_subscription_access(db, organization_id, user=auth.user)
        already_active = bool(access.has_access and access.subscription_status in {"trialing", "active"})

    return {
        "allowed": caps["allowed"],
        "environment": caps["environment"],
        "flag_enabled": caps["flag_enabled"],
        "reason": caps["reason"],
        "already_active": already_active,
    }


@router.post("/activate-trial")
def activate_trial(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Active un essai local (développement / test uniquement).

    Réutilise le schéma de GET /api/subscriptions/current (+ champ outcome).
    """
    if auth.user is None:
        raise HTTPException(401, detail="Authentification requise")

    auth.require("subscription.manage")
    organization_id = auth.require_organization_id()

    result = activate_developer_trial(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
    )
    return {
        "subscription": result.subscription,
        "outcome": result.outcome,
        "environment": result.environment,
    }
