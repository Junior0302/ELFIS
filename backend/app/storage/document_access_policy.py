"""Politique d'accès documentaire — séparation plateforme / org / propriété."""

from __future__ import annotations

from dataclasses import dataclass

from app.deps import AuthContext
from app.storage.storage_exceptions import DocumentAccessDeniedError, StorageValidationError
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject
from app.storage.storage_reject_codes import StorageRejectCode
from app.storage.storage_types import DocumentStatus, DocumentVersionStatus, StorageObjectStatus


@dataclass(frozen=True)
class DocumentAccessDecision:
    allowed: bool
    reason: str = ""


class DocumentAccessPolicy:
    """Autorité d'accès métier documents — backend only."""

    CREATE_PERMS = frozenset({"documents.create", "documents.write", "documents.manage", "*"})
    READ_PERMS = frozenset({"documents.read", "documents.manage", "*"})
    DOWNLOAD_PERMS = frozenset({"documents.download", "documents.read", "documents.manage", "*"})
    ARCHIVE_PERMS = frozenset({"documents.archive", "documents.write", "documents.manage", "*"})
    LINK_PERMS = frozenset({"documents.write", "documents.create", "documents.manage", "*"})
    VERSIONS_READ = frozenset({"documents.versions.read", "documents.read", "documents.manage", "*"})
    VERSIONS_CREATE = frozenset(
        {"documents.versions.create", "documents.create", "documents.manage", "*"}
    )
    DELETE_PERMS = frozenset({"documents.delete", "documents.manage", "*"})
    RESTORE_PERMS = frozenset({"documents.restore", "documents.manage", "*"})
    LEGAL_HOLD_READ = frozenset({"documents.legal_hold.read", "documents.manage", "*"})
    LEGAL_HOLD_MANAGE = frozenset({"documents.legal_hold.manage", "*"})
    QUARANTINE_READ = frozenset({"storage.quarantine.read", "storage.quarantine.manage", "*"})
    QUARANTINE_MANAGE = frozenset({"storage.quarantine.manage", "*"})

    def resolve_organization_id(
        self,
        auth: AuthContext,
        *,
        requested_organization_id: int | None = None,
    ) -> int:
        """Org courante = contexte auth. Un user ordinaire ne peut pas cibler une autre org."""
        org_id = auth.require_organization_id()
        if requested_organization_id is not None and int(requested_organization_id) != int(org_id):
            # Platform admin explicite : uniquement si même header déjà résolu côté deps
            # (membership vérifiée). Refus sinon — pas de spoofing client.
            raise StorageValidationError(
                StorageRejectCode.ORGANIZATION_REQUIRED.value,
                "Organisation non autorisée pour cet acteur",
            )
        return int(org_id)

    def _has(self, auth: AuthContext, allowed: frozenset[str]) -> bool:
        perms = set(auth.permissions or [])
        return bool(perms & allowed)

    def assert_can_create(self, auth: AuthContext) -> None:
        if not self._has(auth, self.CREATE_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Création document refusée")

    def assert_can_read(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.READ_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Lecture refusée")

    def assert_can_download(
        self,
        auth: AuthContext,
        doc: ElfisDocumentRecord,
        obj: ElfisStorageObject | None,
    ) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.DOWNLOAD_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Téléchargement refusé")
        if doc.status in (DocumentStatus.DELETED.value, DocumentStatus.PURGED.value):
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if obj is None:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if obj.status == StorageObjectStatus.QUARANTINED.value:
            if not self._has(auth, self.QUARANTINE_READ):
                raise DocumentAccessDeniedError("object_quarantined", "Document introuvable")
        elif obj.status != StorageObjectStatus.AVAILABLE.value:
            raise DocumentAccessDeniedError("object_unavailable", "Document introuvable")

    def assert_can_archive(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.ARCHIVE_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Archivage refusé")

    def assert_can_link(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.LINK_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Liaison refusée")

    def assert_can_read_versions(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.VERSIONS_READ):
            raise DocumentAccessDeniedError("permission_denied", "Lecture versions refusée")

    def assert_can_create_version(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.VERSIONS_CREATE):
            raise DocumentAccessDeniedError("permission_denied", "Création version refusée")

    def assert_can_download_version(
        self,
        auth: AuthContext,
        doc: ElfisDocumentRecord,
        ver: ElfisDocumentVersion,
        obj: ElfisStorageObject | None,
    ) -> None:
        self.assert_can_download(auth, doc, obj)
        if not self._has(auth, self.VERSIONS_READ):
            raise DocumentAccessDeniedError("permission_denied", "Téléchargement version refusé")
        if ver.status in (DocumentVersionStatus.DELETED.value, DocumentVersionStatus.PURGED.value):
            raise DocumentAccessDeniedError("version_access_denied", "Version introuvable")
        if ver.status == DocumentVersionStatus.QUARANTINED.value:
            if not self._has(auth, self.QUARANTINE_READ):
                raise DocumentAccessDeniedError("object_quarantined", "Version introuvable")

    def assert_can_delete(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.DELETE_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Suppression refusée")

    def assert_can_restore(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.RESTORE_PERMS):
            raise DocumentAccessDeniedError("permission_denied", "Restauration refusée")

    def assert_can_read_legal_hold(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.LEGAL_HOLD_READ):
            raise DocumentAccessDeniedError("permission_denied", "Lecture legal hold refusée")

    def assert_can_manage_legal_hold(self, auth: AuthContext, doc: ElfisDocumentRecord) -> None:
        org_id = auth.require_organization_id()
        if doc.organization_id != org_id:
            raise DocumentAccessDeniedError("document_access_denied", "Document introuvable")
        if not self._has(auth, self.LEGAL_HOLD_MANAGE):
            raise DocumentAccessDeniedError("permission_denied", "Gestion legal hold refusée")

    def can_preview_inline(self, mime: str | None) -> bool:
        allowed = {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/webp",
        }
        return (mime or "").split(";")[0].strip().lower() in allowed
