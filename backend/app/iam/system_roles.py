"""Définitions et bootstrap des rôles système IAM (idempotent)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.iam.permission_catalog import all_permissions
from app.iam.permission_sync import sync_permissions_from_catalog
from app.iam.platform_role_repository import (
    PlatformPermissionRepository,
    PlatformRolePermissionRepository,
    PlatformRoleRepository,
)
from app.iam.role_permission_map import (
    PLATFORM_ADMIN_PERMISSIONS,
    PLATFORM_OPERATOR_PERMISSIONS,
    PLATFORM_SUPPORT_PERMISSIONS,
    PLATFORM_VIEWER_PERMISSIONS,
)

logger = logging.getLogger(__name__)

SYSTEM_ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Toutes les permissions du catalogue. Jamais attribué automatiquement.",
        "permissions": None,  # all known — resolved dynamically + stored as all
    },
    "platform_admin": {
        "name": "Platform Admin",
        "description": "Administration générale ELFIS (sans secrets Vault / refund / impersonation).",
        "permissions": PLATFORM_ADMIN_PERMISSIONS,
    },
    "platform_operator": {
        "name": "Platform Operator",
        "description": "Ops : health, jobs, events, logs, incidents.",
        "permissions": PLATFORM_OPERATOR_PERMISSIONS,
    },
    "platform_support": {
        "name": "Platform Support",
        "description": "Support lecture limitée — aucun secret / Vault / refund.",
        "permissions": PLATFORM_SUPPORT_PERMISSIONS,
    },
    "platform_viewer": {
        "name": "Platform Viewer",
        "description": "Lecture dashboard et System Health.",
        "permissions": PLATFORM_VIEWER_PERMISSIONS,
    },
}


def bootstrap_system_roles(db: Session, *, commit: bool = True) -> dict[str, Any]:
    """Crée/met à jour les rôles système et leurs permissions. Aucun user lié."""
    sync_stats = sync_permissions_from_catalog(db, commit=False)
    role_repo = PlatformRoleRepository(db)
    perm_repo = PlatformPermissionRepository(db)
    link_repo = PlatformRolePermissionRepository(db)

    roles_created = 0
    roles_updated = 0
    links_set = 0

    # Map code → permission id
    perm_ids = {p.code: p.id for p in perm_repo.list_all()}

    for code, meta in SYSTEM_ROLE_DEFINITIONS.items():
        role = role_repo.get_by_code(code)
        if role is None:
            role = role_repo.create(
                code=code,
                name=meta["name"],
                description=meta["description"],
                is_system=True,
                is_active=True,
                commit=False,
            )
            roles_created += 1
        else:
            role.name = meta["name"]
            role.description = meta["description"]
            role.is_system = True
            role.is_active = True
            role_repo.save(role, commit=False)
            roles_updated += 1

        perm_codes = meta["permissions"]
        if perm_codes is None:
            # super_admin : toutes les permissions connues actives
            wanted_ids = [perm_ids[c] for c in sorted(all_permissions()) if c in perm_ids]
        else:
            wanted_ids = [perm_ids[c] for c in sorted(perm_codes) if c in perm_ids]

        link_repo.set_permissions(role.id, wanted_ids, commit=False)
        links_set += len(wanted_ids)

    if commit:
        db.commit()
    else:
        db.flush()

    result = {
        "permissions_sync": sync_stats,
        "roles_created": roles_created,
        "roles_updated": roles_updated,
        "permission_links": links_set,
        "user_assignments": 0,
        "note": "Aucun utilisateur n'a reçu de rôle automatiquement",
    }
    logger.info("iam_system_roles_bootstrapped", extra=result)
    return result
