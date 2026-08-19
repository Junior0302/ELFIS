"""PermissionService — décisions d'accès testables hors FastAPI."""

from __future__ import annotations

from app.iam.permission_catalog import validate_permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    UnknownPermissionError,
)


class PermissionService:
    """Refuse par défaut. Valide les permissions demandées."""

    def has_permission(self, context: PermissionContext, permission: str) -> bool:
        try:
            code = validate_permission(permission)
        except ValueError:
            return False
        if not context.is_authenticated:
            return False
        return context.has(code)

    def has_any_permission(self, context: PermissionContext, permissions: list[str] | tuple[str, ...]) -> bool:
        return any(self.has_permission(context, p) for p in permissions)

    def has_all_permissions(self, context: PermissionContext, permissions: list[str] | tuple[str, ...]) -> bool:
        if not permissions:
            return False
        return all(self.has_permission(context, p) for p in permissions)

    def require_permission(self, context: PermissionContext, permission: str) -> None:
        if not context.is_authenticated:
            raise AuthenticationRequiredError()
        try:
            code = validate_permission(permission)
        except ValueError as exc:
            raise UnknownPermissionError(permission) from exc
        if not context.has(code):
            raise PermissionDeniedError(code)

    def require_any_permission(
        self, context: PermissionContext, permissions: list[str] | tuple[str, ...]
    ) -> None:
        if not context.is_authenticated:
            raise AuthenticationRequiredError()
        codes: list[str] = []
        for p in permissions:
            try:
                codes.append(validate_permission(p))
            except ValueError as exc:
                raise UnknownPermissionError(p) from exc
        if not any(context.has(c) for c in codes):
            raise PermissionDeniedError(codes[0] if codes else None)

    def require_all_permissions(
        self, context: PermissionContext, permissions: list[str] | tuple[str, ...]
    ) -> None:
        if not context.is_authenticated:
            raise AuthenticationRequiredError()
        for p in permissions:
            try:
                code = validate_permission(p)
            except ValueError as exc:
                raise UnknownPermissionError(p) from exc
            if not context.has(code):
                raise PermissionDeniedError(code)
