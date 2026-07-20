"""Contrôle d'accès multi-tenant pour ELFIS Vault."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models_saas import OrganizationMember, Role
from app.services.vault.exceptions import VaultAccessDeniedError

logger = logging.getLogger(__name__)

# Rôles autorisés à archiver (V1) — « employe » = member
VAULT_ARCHIVE_ROLES = frozenset({"owner", "admin", "employe"})
VAULT_ARCHIVE_DENIED_ROLES = frozenset({"comptable", "auditeur", "cfo"})

# Lecture / téléchargement
VAULT_READ_ROLES = frozenset({"owner", "admin", "employe", "comptable", "auditeur", "cfo"})
# Envoi + archivage auto (hors auditeur / cfo lecture seule)
VAULT_DELIVER_ROLES = frozenset({"owner", "admin", "employe", "comptable"})

ACCESS_DENIED_MESSAGE = (
    "Vous n’êtes pas autorisé à archiver un document pour cette entreprise."
)
ORG_ACCESS_DENIED_MESSAGE = "Organisation inaccessible."
DOCUMENT_NOT_FOUND_MESSAGE = "Document introuvable"


def _active_membership_role(
    db: Session, *, user_id: int, organization_id: int
) -> str | None:
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
        return None
    _member, role = row
    return (role.name or "").strip().lower()


def assert_can_archive(db: Session, *, user_id: int, organization_id: int) -> str:
    """Vérifie membership active + rôle autorisé à archiver."""
    role_name = _active_membership_role(db, user_id=user_id, organization_id=organization_id)
    if not role_name:
        logger.info(
            "vault_access_denied",
            extra={"user_id": user_id, "organization_id": organization_id, "reason": "no_membership"},
        )
        raise VaultAccessDeniedError(ACCESS_DENIED_MESSAGE)

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


def assert_can_read(db: Session, *, user_id: int, organization_id: int) -> str:
    """Vérifie membership active + rôle autorisé en lecture."""
    role_name = _active_membership_role(db, user_id=user_id, organization_id=organization_id)
    if not role_name or role_name not in VAULT_READ_ROLES:
        logger.info(
            "vault_read_access_denied",
            extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "reason": "no_membership_or_role",
                "role": role_name,
            },
        )
        raise VaultAccessDeniedError(ORG_ACCESS_DENIED_MESSAGE)
    return role_name


def assert_can_deliver(db: Session, *, user_id: int, organization_id: int) -> str:
    """Rôles autorisés à envoyer un document (archivage Vault + e-mail)."""
    role_name = _active_membership_role(db, user_id=user_id, organization_id=organization_id)
    if not role_name or role_name not in VAULT_DELIVER_ROLES:
        logger.info(
            "vault_deliver_access_denied",
            extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "reason": "no_membership_or_role",
                "role": role_name,
            },
        )
        raise VaultAccessDeniedError(ORG_ACCESS_DENIED_MESSAGE)
    return role_name
