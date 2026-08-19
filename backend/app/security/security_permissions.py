"""Registry central des permissions — compatible rôles existants."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException

from app.deps import AuthContext, get_auth_context
from app.security.security_types import ErrorCode

# Permissions produit déjà en place + codes modules préparés
PERMISSION_REGISTRY: dict[str, str] = {
    # Legacy RBAC
    "invoice.create": "facturation",
    "invoice.delete": "facturation",
    "invoice.read": "facturation",
    "quote.create": "facturation",
    "bank.read": "banque",
    "bank.connect": "banque",
    "tax.manage": "fiscalite",
    "tax.read": "fiscalite",
    "users.invite": "auth",
    "users.manage": "auth",
    "settings.manage": "settings",
    "documents.read": "documents",
    "documents.write": "documents",
    "documents.send_email": "documents",
    "documents.view_email_history": "documents",
    "email_accounts.view": "email",
    "email_accounts.manage": "email",
    "ai.analysis": "analyse-ia",
    "finance.read": "finance",
    "forecast.read": "previsions",
    "reporting.read": "pilotage",
    "subscription.manage": "subscription",
    "sales.read": "sales",
    "sales.write": "sales",
    "sales.manage": "sales",
    "sales.pipeline.manage": "sales",
    "sales.export": "sales",
    "sales.admin": "sales",
    # Modules V1 (mapping vers permissions existantes ou platform)
    "accounting.read": "documents.read",
    "accounting.write": "documents.write",
    "accounting.validate": "documents.write",
    "platform.read": "platform",
    "platform.manage": "platform",
    "billing.read": "subscription.manage",
    "billing.manage": "subscription.manage",
    "ai.execute": "ai.analysis",
    "search.query": "documents.read",
    "notifications.read": "documents.read",
    "jobs.read": "settings.manage",
    "events.read": "settings.manage",
}


def resolve_permission(permission_code: str) -> str:
    """Résout un code module vers une permission RBAC effective si alias."""
    mapped = PERMISSION_REGISTRY.get(permission_code, permission_code)
    # Si l'alias pointe vers une autre clé du registry, un niveau suffit
    if mapped in PERMISSION_REGISTRY and mapped != permission_code:
        return mapped
    return mapped


def require_permission(permission_code: str) -> Callable:
    """Dependency FastAPI — utilisateur actif + permission rôle."""

    async def _dep(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth.user is None:
            raise HTTPException(
                401,
                detail={
                    "code": ErrorCode.AUTHENTICATION_REQUIRED,
                    "message": "Authentification requise",
                },
            )
        if getattr(auth.user, "status", "active") != "active":
            raise HTTPException(
                401,
                detail={"code": ErrorCode.INVALID_TOKEN, "message": "Utilisateur inactif"},
            )
        effective = resolve_permission(permission_code)
        if effective == "platform":
            if not getattr(auth.user, "is_platform_admin", False):
                raise HTTPException(
                    403,
                    detail={
                        "code": ErrorCode.PERMISSION_DENIED,
                        "message": f"Permission refusée: {permission_code}",
                        "permission": permission_code,
                    },
                )
            return auth
        auth.require(effective)
        return auth

    return _dep
