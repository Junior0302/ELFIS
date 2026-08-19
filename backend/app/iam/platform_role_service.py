"""PlatformRoleService — logique métier IAM (hors routes)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.iam import permission_cache as perm_cache
from app.iam.iam_models import ElfisPlatformRole
from app.iam.permission_catalog import all_permissions, is_known_permission
from app.iam.permission_sync import sync_permissions_from_catalog
from app.iam.platform_role_repository import (
    PlatformPermissionRepository,
    PlatformRolePermissionRepository,
    PlatformRoleRepository,
    PlatformUserRoleRepository,
)
from app.iam.system_roles import bootstrap_system_roles
from app.models_saas import User

logger = logging.getLogger(__name__)


class PlatformRoleService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self.roles = PlatformRoleRepository(db)
        self.permissions = PlatformPermissionRepository(db)
        self.role_perms = PlatformRolePermissionRepository(db)
        self.user_roles = PlatformUserRoleRepository(db)

    def sync_catalog(self, *, mark_missing_inactive: bool = False) -> dict[str, Any]:
        return sync_permissions_from_catalog(
            self._db, mark_missing_inactive=mark_missing_inactive, commit=True
        )

    def ensure_system_roles(self) -> dict[str, Any]:
        return bootstrap_system_roles(self._db, commit=True)

    def list_roles(self, *, active_only: bool = False) -> list[ElfisPlatformRole]:
        return self.roles.list_roles(active_only=active_only)

    def get_role(self, role_id: str) -> ElfisPlatformRole | None:
        return self.roles.get_by_id(role_id)

    def get_role_by_code(self, code: str) -> ElfisPlatformRole | None:
        return self.roles.get_by_code(code)

    def create_custom_role(
        self,
        *,
        code: str,
        name: str,
        description: str | None = None,
        permission_codes: list[str] | None = None,
        actor_user_id: int | None = None,
    ) -> ElfisPlatformRole:
        if self.roles.get_by_code(code):
            raise ValueError("role_code_exists")
        for p in permission_codes or []:
            if not is_known_permission(p):
                raise ValueError("unknown_permission")
        role = self.roles.create(
            code=code,
            name=name,
            description=description,
            is_system=False,
            created_by_user_id=actor_user_id,
            commit=False,
        )
        if permission_codes:
            ids = []
            for code_p in permission_codes:
                row = self.permissions.get_by_code(code_p)
                if row:
                    ids.append(row.id)
            self.role_perms.set_permissions(
                role.id, ids, created_by_user_id=actor_user_id, commit=False
            )
        self._db.commit()
        self._db.refresh(role)
        self._audit(
            actor_user_id=actor_user_id,
            action="iam.role.create",
            target=role.code,
            success=True,
        )
        return role

    def set_role_active(
        self, role_id: str, *, is_active: bool, actor_user_id: int | None = None
    ) -> ElfisPlatformRole:
        role = self.roles.get_by_id(role_id)
        if not role:
            raise ValueError("role_not_found")
        if role.is_system and not is_active:
            raise ValueError("system_role_cannot_deactivate")
        role.is_active = is_active
        self.roles.save(role, commit=True)
        self._invalidate_all_users_with_role(role.id)
        self._audit(
            actor_user_id=actor_user_id,
            action="iam.role.deactivate" if not is_active else "iam.role.activate",
            target=role.code,
            success=True,
        )
        return role

    def grant_permission_to_role(
        self,
        role_id: str,
        permission_code: str,
        *,
        actor_user_id: int | None = None,
    ) -> None:
        if not is_known_permission(permission_code):
            raise ValueError("unknown_permission")
        role = self.roles.get_by_id(role_id)
        perm = self.permissions.get_by_code(permission_code)
        if not role or not perm:
            raise ValueError("not_found")
        self.role_perms.grant(
            role.id, perm.id, created_by_user_id=actor_user_id, commit=True
        )
        self._invalidate_all_users_with_role(role.id)
        self._audit(
            actor_user_id=actor_user_id,
            action="iam.role.permission.grant",
            target=f"{role.code}:{permission_code}",
            success=True,
        )

    def revoke_permission_from_role(
        self,
        role_id: str,
        permission_code: str,
        *,
        actor_user_id: int | None = None,
    ) -> None:
        role = self.roles.get_by_id(role_id)
        perm = self.permissions.get_by_code(permission_code)
        if not role or not perm:
            raise ValueError("not_found")
        self.role_perms.revoke(role.id, perm.id, commit=True)
        self._invalidate_all_users_with_role(role.id)
        self._audit(
            actor_user_id=actor_user_id,
            action="iam.role.permission.revoke",
            target=f"{role.code}:{permission_code}",
            success=True,
        )

    def assign_role_to_user(
        self,
        user_id: int,
        role_code: str,
        *,
        actor_user_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        user = self._db.get(User, user_id)
        role = self.roles.get_by_code(role_code)
        if not user:
            raise ValueError("user_not_found")
        if not role or not role.is_active:
            raise ValueError("role_not_found")
        self.user_roles.assign(
            user_id=user_id,
            role_id=role.id,
            assigned_by_user_id=actor_user_id,
            expires_at=expires_at,
            commit=True,
        )
        perm_cache.effective_permissions_cache.invalidate_user(user_id)
        self._audit(
            actor_user_id=actor_user_id,
            action="iam.user.role.assign",
            target=f"user:{user_id}:role:{role_code}",
            success=True,
        )

    def revoke_role_from_user(
        self,
        user_id: int,
        role_code: str,
        *,
        actor_user_id: int | None = None,
    ) -> None:
        role = self.roles.get_by_code(role_code)
        if not role:
            raise ValueError("role_not_found")
        ok = self.user_roles.revoke(user_id, role.id, commit=True)
        perm_cache.effective_permissions_cache.invalidate_user(user_id)
        self._audit(
            actor_user_id=actor_user_id,
            action="iam.user.role.revoke",
            target=f"user:{user_id}:role:{role_code}",
            success=ok,
        )
        if not ok:
            raise ValueError("assignment_not_found")

    def list_user_roles(self, user_id: int) -> list[dict[str, Any]]:
        pairs = self.user_roles.list_active_roles_with_codes(user_id)
        return [
            {
                "role_id": role.id,
                "code": role.code,
                "name": role.name,
                "is_system": role.is_system,
                "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None,
            }
            for assignment, role in pairs
        ]

    def effective_permissions_for_user(self, user_id: int) -> frozenset[str]:
        cache_key = f"user:{user_id}"
        cached = perm_cache.effective_permissions_cache.get(cache_key)
        if cached is not None:
            return cached

        perms: set[str] = set()
        pairs = self.user_roles.list_active_roles_with_codes(user_id)
        for _assignment, role in pairs:
            if role.code == "super_admin":
                result = all_permissions()
                perm_cache.effective_permissions_cache.set(cache_key, result)
                return result
            for code in self.role_perms.list_permission_codes_for_role(role.id):
                perms.add(code)

        result = frozenset(perms)
        perm_cache.effective_permissions_cache.set(cache_key, result)
        return result

    def _invalidate_all_users_with_role(self, role_id: str) -> None:
        # Invalidation large : clear cache (TTL court) — simple et sûr
        perm_cache.effective_permissions_cache.clear()

    def _audit(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        target: str,
        success: bool,
        correlation_id: str | None = None,
    ) -> None:
        logger.info(
            "iam_audit",
            extra={
                "actor_user_id": actor_user_id,
                "action": action,
                "target": target,
                "success": success,
                "correlation_id": correlation_id,
            },
        )
        try:
            from app.audit.audit_logger import AuditLogger

            al = AuditLogger(isolated_writes=True)
            # target format user:{id}:role:{code}
            target_user_id = 0
            role_code = ""
            parts = target.split(":")
            if len(parts) >= 4 and parts[0] == "user":
                try:
                    target_user_id = int(parts[1])
                except ValueError:
                    target_user_id = 0
                role_code = parts[3] if len(parts) > 3 else ""
            if action.endswith(".assign"):
                al.record_role_assignment(
                    actor_user_id=actor_user_id,
                    target_user_id=target_user_id,
                    role_code=role_code or "unknown",
                    success=success,
                )
            elif action.endswith(".revoke"):
                al.record_role_removal(
                    actor_user_id=actor_user_id,
                    target_user_id=target_user_id,
                    role_code=role_code or "unknown",
                    success=success,
                )
        except Exception:  # noqa: BLE001
            logger.warning("iam_audit_engine_bridge_failed", exc_info=True)
