"""ELFIS IAM — Permission Engine (RC2.2).

Étape 1 : moteur + mapping de compatibilité.
Étape 2 : rôles/permissions plateforme persistants (elfis_platform_*).
Le RBAC organisation (tables roles/permissions SaaS) reste distinct.
"""

from app.iam.permission_catalog import Permission, all_permissions, is_known_permission
from app.iam.permission_context import PermissionContext
from app.iam.permission_service import PermissionService

__all__ = [
    "Permission",
    "PermissionContext",
    "PermissionService",
    "all_permissions",
    "is_known_permission",
]
