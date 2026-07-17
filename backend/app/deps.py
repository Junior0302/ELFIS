from __future__ import annotations

from datetime import datetime

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models_saas import Organization, User
from app.services.auth import decode_token, get_user_memberships, user_has_permission


class AuthContext:
    def __init__(
        self,
        user: User | None,
        organization_id: int | None,
        role: str | None,
        permissions: list[str],
    ):
        self.user = user
        self.organization_id = organization_id
        self.role = role
        self.permissions = permissions

    def require(self, permission: str) -> None:
        if self.user is None:
            raise HTTPException(401, detail="Authentification requise")
        if not user_has_permission(self.permissions, permission):
            raise HTTPException(
                403,
                detail={
                    "code": "permission_denied",
                    "message": f"Permission refusée: {permission}",
                    "permission": permission,
                },
            )

    def require_organization_id(self) -> int:
        if self.organization_id is None:
            raise HTTPException(
                403,
                detail={
                    "code": "organization_required",
                    "message": "Une organisation active doit être sélectionnée",
                },
            )
        return self.organization_id


def get_auth_context(
    authorization: str | None = Header(default=None),
    x_organization_id: int | None = Header(default=None, alias="X-Organization-Id"),
    db: Session = Depends(get_db),
) -> AuthContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        if settings.auth_required:
            raise HTTPException(401, detail="Authentification requise")
        return AuthContext(None, x_organization_id, None, ["*"])

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(401, detail="Token invalide")

    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(401, detail="Utilisateur inactif")

    memberships = get_user_memberships(db, user.id)
    if not memberships:
        raise HTTPException(
            403,
            detail={
                "code": "organization_access_denied",
                "message": "Aucune organisation active",
            },
        )

    org_id = x_organization_id or int(payload.get("org_id") or memberships[0]["organization_id"])
    current = next((m for m in memberships if m["organization_id"] == org_id), None)
    if not current:
        raise HTTPException(
            403,
            detail={
                "code": "organization_access_denied",
                "message": "Accès organisation refusé",
            },
        )

    return AuthContext(user, org_id, current["role"], current["permissions"])


def _is_platform_admin_user(user: User | None) -> bool:
    if not user or user.status != "active":
        return False
    if user.is_platform_admin:
        return True
    return user.email.lower() in settings.platform_admin_email_set


def require_active_subscription(
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthContext:
    organization_id = auth.require_organization_id()
    if not db.get(Organization, organization_id):
        raise HTTPException(
            403,
            detail={"code": "organization_not_found", "message": "Organisation introuvable"},
        )
    if auth.user is None and not settings.auth_required:
        return auth

    if _is_platform_admin_user(auth.user):
        if not auth.user.is_platform_admin:
            auth.user.is_platform_admin = True
            db.add(auth.user)
            db.commit()
            db.refresh(auth.user)
        return auth

    from app.subscriptions.access import get_subscription_access
    from app.subscriptions.permissions import subscription_error

    access = get_subscription_access(db, organization_id, user=auth.user)
    if access.has_access and access.read_only and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        raise HTTPException(
            402,
            detail={
                **subscription_error("PAYMENT_REQUIRED", status=access.subscription_status, action="UPDATE_PAYMENT"),
                "code": "subscription_past_due_read_only",
                "message": (
                    "Le paiement a échoué : l’accès reste disponible en lecture seule "
                    "pendant la période de grâce"
                ),
                "status": access.raw_status,
            },
        )
    if not access.has_access:
        code = "SUBSCRIPTION_SUSPENDED" if access.admin_revoked else "SUBSCRIPTION_REQUIRED"
        action = "CONTACT_SUPPORT" if access.admin_revoked else "START_TRIAL"
        if access.subscription_status in {"canceled", "expired"}:
            code = "SUBSCRIPTION_CANCELED"
            action = "REACTIVATE"
        raise HTTPException(
            402,
            detail={
                **subscription_error(code, status=access.subscription_status, action=action),
                "code": "subscription_inactive" if access.subscription_id else "subscription_required",
                "message": access.label
                if access.admin_revoked
                else (
                    "Un abonnement ComptaPilot Pro est requis"
                    if not access.subscription_id
                    else "L’abonnement ComptaPilot Pro n’est pas actif"
                ),
                "status": access.subscription_status,
            },
        )
    return auth


def require_platform_admin(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, detail="Authentification requise")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload or "sub" not in payload:
        raise HTTPException(401, detail="Token invalide")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(401, detail="Utilisateur inactif")
    if not _is_platform_admin_user(user):
        raise HTTPException(
            403,
            detail={
                "code": "platform_admin_required",
                "message": "Accès super-administrateur requis",
            },
        )
    if not user.is_platform_admin:
        user.is_platform_admin = True
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
