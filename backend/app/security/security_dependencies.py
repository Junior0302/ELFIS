"""Dépendances sécurité réutilisables."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_platform_admin
from app.models_saas import Organization, User
from app.security.security_permissions import require_permission
from app.security.security_types import ErrorCode
from sqlalchemy.orm import Session


def require_active_user(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.user is None:
        raise HTTPException(
            401,
            detail={"code": ErrorCode.AUTHENTICATION_REQUIRED, "message": "Authentification requise"},
        )
    if auth.user.status != "active":
        raise HTTPException(
            401,
            detail={"code": ErrorCode.INVALID_TOKEN, "message": "Utilisateur inactif"},
        )
    return auth


def require_organization_not_suspended_for_write(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
    method: str = "GET",
) -> AuthContext:
    """Helper — la logique principale reste dans require_active_subscription."""
    org_id = auth.organization_id
    if org_id is None:
        return auth
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(
            404,
            detail={"code": ErrorCode.ORGANIZATION_NOT_FOUND, "message": "Organisation introuvable"},
        )
    status = getattr(org, "platform_status", None) or "active"
    if status == "suspended" and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        raise HTTPException(
            403,
            detail={
                "code": ErrorCode.ORGANIZATION_SUSPENDED,
                "message": "Organisation suspendue — écriture interdite",
            },
        )
    return auth


def optional_metrics_token(
    authorization: str | None = Header(default=None),
    x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token"),
    db: Session = Depends(get_db),
) -> User | None:
    """Auth metrics : platform admin OU token interne optionnel."""
    expected = (getattr(settings, "elfis_metrics_token", "") or "").strip()
    if expected and x_metrics_token and x_metrics_token == expected:
        return None  # token interne OK sans user
    if not getattr(settings, "elfis_metrics_require_auth", True):
        return None
    return require_platform_admin(authorization=authorization, db=db)


__all__ = [
    "require_permission",
    "require_active_user",
    "require_organization_not_suspended_for_write",
    "optional_metrics_token",
    "require_platform_admin",
]
