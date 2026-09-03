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

    def require_any(self, permissions: list[str]) -> None:
        if self.user is None:
            raise HTTPException(401, detail="Authentification requise")
        if any(user_has_permission(self.permissions, p) for p in permissions):
            return
        raise HTTPException(
            403,
            detail={
                "code": "permission_denied",
                "message": "Permission refusée",
                "permission": permissions[0] if permissions else None,
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

    @property
    def user_id(self) -> int | None:
        return self.user.id if self.user is not None else None


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
    org = db.get(Organization, organization_id)
    if not org:
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

    if not getattr(settings, "elfis_billing_enabled", True):
        return auth

    platform_status = getattr(org, "platform_status", None) or "active"
    if platform_status == "suspended" and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        raise HTTPException(
            403,
            detail={
                "code": "organization_suspended",
                "message": "Organisation suspendue par la plateforme. Consultation seule autorisée.",
            },
        )

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


DEVELOPER_COCKPIT_PERMISSIONS = frozenset(
    {
        "platform.developer",
        "platform.engineer",
        "platform.sre",
        "platform.cto",
        "platform.admin",
    }
)


def require_developer_cockpit(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Accès Cockpit Développeur : platform admin (flag) OU permission technique explicite.

    Les permissions developer/engineer/sre/cto ne sont PAS auto-attribuées
    via PLATFORM_ADMIN_PERMISSIONS.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, detail="Authentification requise")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload or "sub" not in payload:
        raise HTTPException(401, detail="Token invalide")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != "active":
        raise HTTPException(401, detail="Utilisateur inactif")

    if _is_platform_admin_user(user):
        if not user.is_platform_admin:
            user.is_platform_admin = True
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    try:
        from app.iam.permission_resolver import PermissionResolver

        ctx = PermissionResolver().resolve(user=user, db=db, is_platform_admin=False)
        codes = set(ctx.permissions or [])
        if codes & DEVELOPER_COCKPIT_PERMISSIONS:
            return user
    except Exception:  # noqa: BLE001
        pass

    raise HTTPException(
        403,
        detail={
            "code": "developer_cockpit_forbidden",
            "message": "Accès Cockpit Développeur requis (platform.admin ou platform.developer|engineer|sre|cto)",
        },
    )
