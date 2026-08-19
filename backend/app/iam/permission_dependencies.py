"""Dépendances FastAPI — Permission Engine (indépendant du RBAC produit).

Note : `app.security.security_permissions.require_permission` reste le gate
tenant/produit basé sur AuthContext. Ici, les gates plateforme utilisent
Bearer + User comme require_platform_admin, puis le catalogue IAM.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import _is_platform_admin_user
from app.iam.permission_catalog import Permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    UnknownPermissionError,
)
from app.iam.permission_resolver import PermissionResolver
from app.iam.permission_service import PermissionService
from app.models_saas import User
from app.services.auth import decode_token

logger = logging.getLogger(__name__)

_resolver = PermissionResolver()
_service = PermissionService()


def _correlation_id(request: Request | None) -> str | None:
    if request is None:
        return None
    return (
        request.headers.get("X-Correlation-Id")
        or request.headers.get("X-Request-Id")
        or getattr(getattr(request, "state", None), "correlation_id", None)
    )


def _log_denial(
    *,
    request: Request | None,
    user_id: int | None,
    permission: str | None,
    organization_id: int | None,
    reason: str,
) -> None:
    path = getattr(request, "url", None)
    route = str(path.path) if path is not None else None
    method = getattr(request, "method", None)
    corr = _correlation_id(request)
    logger.warning(
        "iam_permission_denied",
        extra={
            "user_id": user_id,
            "permission": permission,
            "route": route,
            "method": method,
            "organization_id": organization_id,
            "correlation_id": corr,
            "reason": reason,
        },
    )
    try:
        from app.audit.audit_logger import AuditLogger

        AuditLogger(isolated_writes=True).record_permission_denied(
            user_id=user_id,
            permission=permission,
            route=route,
            method=method,
            organization_id=organization_id,
            reason=reason,
            correlation_id=corr,
        )
    except Exception:  # noqa: BLE001
        logger.warning("audit_permission_denied_bridge_failed", exc_info=True)


def build_permission_context_for_user(
    user: User,
    *,
    organization_id: int | None = None,
    organization_role_name: str | None = None,
    correlation_id: str | None = None,
) -> PermissionContext:
    """Construit un contexte depuis un User déjà chargé (tests / services)."""
    return _resolver.resolve(
        user=user,
        organization_id=organization_id,
        organization_role_name=organization_role_name,
        is_platform_admin=_is_platform_admin_user(user),
        correlation_id=correlation_id,
        db=None,
    )


def get_permission_context(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> PermissionContext:
    """Charge l'utilisateur Bearer et résout les permissions (côté serveur uniquement)."""
    corr = _correlation_id(request)
    if not authorization or not authorization.lower().startswith("bearer "):
        return PermissionContext(is_authenticated=False, correlation_id=corr)

    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload or "sub" not in payload:
        return PermissionContext(is_authenticated=False, correlation_id=corr)

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return PermissionContext(is_authenticated=False, correlation_id=corr)

    user = db.get(User, user_id)
    if not user or user.status != "active":
        return PermissionContext(is_authenticated=False, correlation_id=corr)

    # Sync allowlist → flag (même comportement que require_platform_admin)
    is_admin = _is_platform_admin_user(user)
    if is_admin and not user.is_platform_admin:
        user.is_platform_admin = True
        db.add(user)
        db.commit()
        db.refresh(user)

    org_id = None
    raw_org = payload.get("org_id")
    if raw_org is not None:
        try:
            org_id = int(raw_org)
        except (TypeError, ValueError):
            org_id = None

    return _resolver.resolve(
        user=user,
        organization_id=org_id,
        is_platform_admin=is_admin,
        correlation_id=corr,
        db=db,
    )


def _raise_http(exc: Exception, *, request: Request | None, ctx: PermissionContext, permission: str | None) -> None:
    if isinstance(exc, AuthenticationRequiredError):
        _log_denial(
            request=request,
            user_id=ctx.user_id,
            permission=permission,
            organization_id=ctx.organization_id,
            reason="unauthenticated",
        )
        raise HTTPException(
            401,
            detail={"code": "authentication_required", "message": "Authentification requise"},
        ) from exc
    if isinstance(exc, UnknownPermissionError):
        _log_denial(
            request=request,
            user_id=ctx.user_id,
            permission=permission,
            organization_id=ctx.organization_id,
            reason="unknown_permission",
        )
        # Ne pas lister le catalogue — message générique
        raise HTTPException(
            403,
            detail={"code": "permission_denied", "message": "Accès refusé"},
        ) from exc
    if isinstance(exc, PermissionDeniedError):
        _log_denial(
            request=request,
            user_id=ctx.user_id,
            permission=permission or getattr(exc, "permission", None),
            organization_id=ctx.organization_id,
            reason="denied",
        )
        raise HTTPException(
            403,
            detail={"code": "permission_denied", "message": "Accès refusé"},
        ) from exc
    raise exc


def require_permission(permission: str) -> Callable:
    """Dependency FastAPI : exige une permission IAM connue."""

    def _dep(
        request: Request,
        ctx: PermissionContext = Depends(get_permission_context),
    ) -> PermissionContext:
        try:
            _service.require_permission(ctx, permission)
        except (AuthenticationRequiredError, PermissionDeniedError, UnknownPermissionError) as exc:
            _raise_http(exc, request=request, ctx=ctx, permission=permission)
        return ctx

    return _dep


def require_any_permission(*permissions: str) -> Callable:
    def _dep(
        request: Request,
        ctx: PermissionContext = Depends(get_permission_context),
    ) -> PermissionContext:
        try:
            _service.require_any_permission(ctx, permissions)
        except (AuthenticationRequiredError, PermissionDeniedError, UnknownPermissionError) as exc:
            _raise_http(exc, request=request, ctx=ctx, permission=permissions[0] if permissions else None)
        return ctx

    return _dep


def require_all_permissions(*permissions: str) -> Callable:
    def _dep(
        request: Request,
        ctx: PermissionContext = Depends(get_permission_context),
    ) -> PermissionContext:
        try:
            _service.require_all_permissions(ctx, permissions)
        except (AuthenticationRequiredError, PermissionDeniedError, UnknownPermissionError) as exc:
            _raise_http(exc, request=request, ctx=ctx, permission=permissions[0] if permissions else None)
        return ctx

    return _dep


# Raccourcis System Health (évite les chaînes magiques dans le router)
require_system_health_read = require_permission(Permission.SYSTEM_HEALTH_READ.value)
require_system_metrics_read = require_permission(Permission.SYSTEM_METRICS_READ.value)
require_system_alerts_read = require_permission(Permission.SYSTEM_ALERTS_READ.value)
require_system_logs_read = require_permission(Permission.SYSTEM_LOGS_READ.value)
