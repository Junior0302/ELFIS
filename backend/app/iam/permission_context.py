"""PermissionContext — contexte d'une décision d'accès (jamais fourni par le frontend)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PermissionContext:
    user_id: int | None = None
    organization_id: int | None = None
    platform_role: str = "none"
    organization_role: str = "none"
    permissions: frozenset[str] = field(default_factory=frozenset)
    is_authenticated: bool = False
    is_platform_admin: bool = False
    is_super_admin: bool = False
    product_id: str | None = None
    correlation_id: str | None = None

    def has(self, permission: str) -> bool:
        return permission in self.permissions
