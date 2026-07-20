"""Orchestration d'archivage ELFIS Vault."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models_vault import VaultDocument
from app.repositories.vault_repository import VaultRepository
from app.schemas_vault import (
    VaultActivityAction,
    VaultArchiveFormMeta,
    VaultDocumentResponse,
    VaultDocumentType,
)
from app.services.vault.checksum_service import calculate_sha256
from app.services.vault.exceptions import (
    VaultDatabaseError,
    VaultDuplicateDocumentError,
    VaultFileTooLargeError,
    VaultInvalidFileError,
    VaultStorageError,
)
from app.services.vault.storage_service import VaultStorageService, build_storage_path
from app.services.vault.vault_access_service import assert_can_archive

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"
ALLOWED_MIME = {"application/pdf", "application/x-pdf"}


def _validate_pdf(*, filename: str | None, content_type: str | None, content: bytes) -> None:
    if not content:
        raise VaultInvalidFileError("Fichier vide")

    max_bytes = max(1, settings.elfis_vault_max_file_size_mb) * 1024 * 1024
    if len(content) > max_bytes:
        raise VaultFileTooLargeError(settings.elfis_vault_max_file_size_mb)

    ext = Path(filename or "").suffix.lower()
    if ext != ".pdf":
        raise VaultInvalidFileError("Seuls les fichiers PDF sont acceptés")

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime and mime not in ALLOWED_MIME and mime != "application/octet-stream":
        raise VaultInvalidFileError("Type MIME non autorisé (application/pdf requis)")

    if not content.startswith(PDF_MAGIC):
        raise VaultInvalidFileError("Signature PDF invalide")


def _to_response(doc: VaultDocument) -> VaultDocumentResponse:
    return VaultDocumentResponse(
        id=doc.id,
        tenant_id=doc.organization_id,
        document_type=VaultDocumentType(doc.document_type),
        document_number=doc.document_number,
        original_filename=doc.original_filename,
        storage_path=doc.storage_path,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        checksum_sha256=doc.checksum_sha256,
        archive_status=doc.archive_status,  # type: ignore[arg-type]
        accounting_status=doc.accounting_status,  # type: ignore[arg-type]
        email_status=doc.email_status,  # type: ignore[arg-type]
        version=doc.version,
        archived_at=doc.archived_at,
        created_at=doc.created_at,
    )


def archive_document(
    db: Session,
    *,
    user_id: int,
    meta: VaultArchiveFormMeta,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    storage: VaultStorageService | None = None,
) -> VaultDocumentResponse:
    """Archive un PDF dans ELFIS Vault (accès → checksum → doublon → storage → DB → log)."""
    assert_can_archive(db, user_id=user_id, organization_id=meta.tenant_id)
    _validate_pdf(filename=filename, content_type=content_type, content=content)

    checksum = calculate_sha256(content)
    repo = VaultRepository(db)
    duplicate = repo.find_duplicate(
        organization_id=meta.tenant_id,
        checksum_sha256=checksum,
    )
    if duplicate:
        raise VaultDuplicateDocumentError(duplicate.id)

    original_filename = Path(filename or "document.pdf").name
    storage_path = build_storage_path(
        organization_id=meta.tenant_id,
        document_type=meta.document_type,
        original_filename=original_filename,
    )

    storage_svc = storage or VaultStorageService()
    try:
        storage_svc.upload_pdf(storage_path=storage_path, content=content)
    except VaultStorageError:
        raise
    except Exception as exc:
        logger.error("vault_upload_unexpected")
        raise VaultStorageError("Stockage temporairement indisponible") from exc

    try:
        doc = repo.create_document(
            organization_id=meta.tenant_id,
            document_type=meta.document_type,
            document_number=meta.document_number,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type="application/pdf",
            file_size=len(content),
            checksum_sha256=checksum,
            invoice_date=meta.invoice_date,
            due_date=meta.due_date,
            amount_ht=meta.amount_ht,
            amount_vat=meta.amount_vat,
            amount_ttc=meta.amount_ttc,
            currency=meta.currency,
            customer_id=meta.customer_id,
            supplier_id=meta.supplier_id,
            archived_by_user_id=user_id,
        )
    except VaultDatabaseError:
        storage_svc.delete_file(storage_path=storage_path)
        raise
    except Exception as exc:
        storage_svc.delete_file(storage_path=storage_path)
        logger.exception("vault_db_insert_unexpected")
        raise VaultDatabaseError("Échec d'enregistrement du document") from exc

    try:
        repo.create_activity_log(
            organization_id=meta.tenant_id,
            document_id=doc.id,
            user_id=user_id,
            action=VaultActivityAction.document_archived,
            metadata={
                "original_filename": original_filename,
                "storage_path": storage_path,
                "file_size": len(content),
                "checksum_sha256": checksum,
                "document_type": meta.document_type.value,
            },
        )
    except Exception:
        logger.exception(
            "vault_activity_log_failed_after_archive",
            extra={"document_id": doc.id, "organization_id": meta.tenant_id},
        )

    return _to_response(doc)
