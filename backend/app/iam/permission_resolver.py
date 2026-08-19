"""PermissionResolver — hybride : rôles IAM persistants + compatibilité historique."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.iam.permission_catalog import all_permissions
from app.iam.permission_context import PermissionContext
from app.iam.permission_types import ORG_ROLE_ALIASES, OrganizationRole, PlatformRole
from app.iam.role_permission_map import (
    ORGANIZATION_ROLE_PERMISSIONS,
    PLATFORM_ADMIN_PERMISSIONS,
    PLATFORM_ROLE_PERMISSIONS,
)


class PermissionResolver:
    """Résout un PermissionContext.

    Ordre :
    1. utilisateur authentifié actif
    2. rôles IAM persistants actifs / non expirés
    3. compatibilité is_platform_admin / allowlist (mapping historique)
    4. rôles organisation (jamais de permissions plateforme)
    5. fusion sans doublons ; refus par défaut
    """

    def resolve(
        self,
        *,
        user: Any | None = None,
        organization_id: int | None = None,
        organization_role_name: str | None = None,
        is_platform_admin: bool = False,
        force_platform_role: str | None = None,
        product_id: str | None = None,
        correlation_id: str | None = None,
        db: Session | None = None,
    ) -> PermissionContext:
        if user is None:
            return PermissionContext(
                is_authenticated=False,
                correlation_id=correlation_id,
            )

        user_id = int(getattr(user, "id", 0) or 0) or None
        status = getattr(user, "status", None) or "active"
        if status != "active":
            return PermissionContext(
                user_id=user_id,
                is_authenticated=False,
                correlation_id=correlation_id,
            )

        permissions: set[str] = set()
        persistent_codes: list[str] = []
        is_super = False

        # --- Rôles IAM persistants ---
        if db is not None and user_id is not None:
            try:
                from app.iam.platform_role_service import PlatformRoleService

                svc = PlatformRoleService(db)
                pairs = svc.user_roles.list_active_roles_with_codes(user_id)
                for _assignment, role in pairs:
                    persistent_codes.append(role.code)
                    if role.code == PlatformRole.SUPER_ADMIN.value:
                        is_super = True
                if is_super:
                    permissions = set(all_permissions())
                elif pairs:
                    permissions |= set(svc.effective_permissions_for_user(user_id))
            except Exception:
                # Tables absentes (migration non appliquée) → compatibilité seule
                persistent_codes = []

        # --- Compatibilité historique / force ---
        compat_role = PlatformRole.NONE.value
        if force_platform_role:
            compat_role = str(force_platform_role).strip().lower()
            if compat_role == PlatformRole.SUPER_ADMIN.value:
                is_super = True
                permissions = set(all_permissions())
            else:
                mapped = PLATFORM_ROLE_PERMISSIONS.get(compat_role)
                if mapped is not None:
                    permissions |= set(mapped)
        elif is_platform_admin and not is_super:
            compat_role = PlatformRole.PLATFORM_ADMIN.value
            permissions |= set(PLATFORM_ADMIN_PERMISSIONS)

        # --- Rôles organisation (jamais plateforme) ---
        org_role = OrganizationRole.NONE.value
        if organization_role_name:
            alias = ORG_ROLE_ALIASES.get(organization_role_name.strip().lower())
            if alias is not None:
                org_role = alias.value
                org_set = ORGANIZATION_ROLE_PERMISSIONS.get(org_role)
                if org_set:
                    permissions |= set(org_set)

        platform_role = self._display_platform_role(
            persistent_codes=persistent_codes,
            compat_role=compat_role,
            is_super=is_super,
            is_platform_admin=is_platform_admin,
        )

        return PermissionContext(
            user_id=user_id,
            organization_id=organization_id,
            platform_role=platform_role,
            organization_role=org_role,
            permissions=frozenset(permissions),
            is_authenticated=True,
            is_platform_admin=bool(is_platform_admin)
            or platform_role
            in {
                PlatformRole.PLATFORM_ADMIN.value,
                PlatformRole.SUPER_ADMIN.value,
            }
            or PlatformRole.PLATFORM_ADMIN.value in persistent_codes,
            is_super_admin=is_super,
            product_id=product_id,
            correlation_id=correlation_id,
        )

    def _display_platform_role(
        self,
        *,
        persistent_codes: list[str],
        compat_role: str,
        is_super: bool,
        is_platform_admin: bool,
    ) -> str:
        if is_super or PlatformRole.SUPER_ADMIN.value in persistent_codes:
            return PlatformRole.SUPER_ADMIN.value
        priority = (
            PlatformRole.PLATFORM_ADMIN.value,
            PlatformRole.PLATFORM_OPERATOR.value,
            PlatformRole.PLATFORM_SUPPORT.value,
            PlatformRole.PLATFORM_VIEWER.value,
        )
        for code in priority:
            if code in persistent_codes:
                return code
        if compat_role and compat_role != PlatformRole.NONE.value:
            return compat_role
        if is_platform_admin:
            return PlatformRole.PLATFORM_ADMIN.value
        return PlatformRole.NONE.value
