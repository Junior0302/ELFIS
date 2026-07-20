"""Contrôle d'accès multi-tenant pour ELFIS Vault."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models_saas import OrganizationMember, Role
from app.services.vault.exceptions import VaultAccessDeniedError

logger = logging.getLogger(__name__)

# Rôles autorisés à archiver (V1) — « employe » = member
VAULT_ARCHIVE_ROLES = frozenset({"owner", "admin", "employe"})
# Comptable / lecture seule (et CFO hors liste V1)
VAULT_ARCHIVE_DENIED_ROLES = frozenset({"comptable", "auditeur", "cfo"})

ACCESS_DENIED_MESSAGE = (
    "Vous n’êtes pas autorisé à archiver un document pour cette entreprise."
)


def assert_can_archive(db: Session, *, user_id: int, organization_id: int) -> str:
    """Vérifie membership active + rôle autorisé.

    Ne révèle jamais si l'organisation existe ou non.
    Retourne le nom du rôle en cas de succès.
    """
    row = (
        db.query(OrganizationMember, Role)
        .join(Role, Role.id == OrganizationMember.role_id)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
        )
        .first()
    )
    if not row:
        logger.info(
            "vault_access_denied",
            extra={"user_id": user_id, "organization_id": organization_id, "reason": "no_membership"},
        )
        raise VaultAccessDeniedError(ACCESS_DENIED_MESSAGE)

    _member, role = row
    role_name = (role.name or "").strip().lower()
    if role_name in VAULT_ARCHIVE_DENIED_ROLES or role_name not in VAULT_ARCHIVE_ROLES:
        logger.info(
            "vault_access_denied",
            extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "reason": "role_denied",
                "role": role_name,
            },
        )
        raise VaultAccessDeniedError(ACCESS_DENIED_MESSAGE)

    return role_name
