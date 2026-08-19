"""Synchronisation permission_catalog → elfis_platform_permissions."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.iam.permission_catalog import Permission, all_permissions, is_known_permission
from app.iam.platform_role_repository import PlatformPermissionRepository

logger = logging.getLogger(__name__)


def _split_code(code: str) -> tuple[str, str]:
    resource, _, action = code.partition(".")
    # resource.action or resource.sub.action → resource = first, action = rest
    parts = code.split(".")
    if len(parts) < 2:
        return code, ""
    return parts[0], ".".join(parts[1:])


def sync_permissions_from_catalog(
    db: Session,
    *,
    mark_missing_inactive: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    """Crée/met à jour les permissions du catalogue. Jamais de suppression.

    mark_missing_inactive=True : permissions DB absentes du catalogue → is_active=False.
    """
    repo = PlatformPermissionRepository(db)
    known = all_permissions()
    created = 0
    updated = 0
    unchanged = 0
    inactivated = 0

    for code in sorted(known):
        resource, action = _split_code(code)
        existing = repo.get_by_code(code)
        if existing is None:
            repo.upsert(
                code=code,
                resource=resource,
                action=action,
                description=f"Permission catalogue {code}",
                is_active=True,
                commit=False,
            )
            created += 1
        else:
            changed = (
                existing.resource != resource
                or existing.action != action
                or not existing.is_active
            )
            if changed:
                repo.upsert(
                    code=code,
                    resource=resource,
                    action=action,
                    description=existing.description or f"Permission catalogue {code}",
                    is_active=True,
                    commit=False,
                )
                updated += 1
            else:
                unchanged += 1

    if mark_missing_inactive:
        for row in repo.list_all():
            if row.code not in known and row.is_active:
                if not is_known_permission(row.code):
                    row.is_active = False
                    db.add(row)
                    inactivated += 1

    if commit:
        db.commit()
    else:
        db.flush()

    result = {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "inactivated": inactivated,
        "catalog_size": len(known),
    }
    logger.info("iam_permissions_synced", extra=result)
    return result


def assert_permission_known(code: str) -> str:
    if not is_known_permission(code):
        raise ValueError("permission inconnue du catalogue")
    return code


# Export Permission for bootstrap convenience
SYSTEM_PERMISSION_CODES = frozenset(p.value for p in Permission)
