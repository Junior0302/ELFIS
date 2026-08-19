"""Types et constantes IAM."""

from __future__ import annotations

from enum import Enum


class PlatformRole(str, Enum):
    """Profils plateforme (compatibilité + futurs rôles)."""

    SUPER_ADMIN = "super_admin"
    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_OPERATOR = "platform_operator"
    PLATFORM_SUPPORT = "platform_support"
    PLATFORM_VIEWER = "platform_viewer"
    PLATFORM_DEVELOPER = "platform_developer"
    PLATFORM_ENGINEER = "platform_engineer"
    PLATFORM_SRE = "platform_sre"
    PLATFORM_CTO = "platform_cto"
    NONE = "none"


class OrganizationRole(str, Enum):
    """Profils organisation (mapping depuis les rôles RBAC existants)."""

    ORGANIZATION_ADMIN = "organization_admin"
    ORGANIZATION_MANAGER = "organization_manager"
    ORGANIZATION_MEMBER = "organization_member"
    VIEWER = "viewer"
    NONE = "none"


# Alias rôles org existants (table roles.name) → profil IAM
ORG_ROLE_ALIASES: dict[str, OrganizationRole] = {
    "owner": OrganizationRole.ORGANIZATION_ADMIN,
    "admin": OrganizationRole.ORGANIZATION_ADMIN,
    "cfo": OrganizationRole.ORGANIZATION_MANAGER,
    "comptable": OrganizationRole.ORGANIZATION_MEMBER,
    "employe": OrganizationRole.ORGANIZATION_MEMBER,
    "auditeur": OrganizationRole.VIEWER,
}
