"""Orchestration d'archivage et consultation ELFIS Vault."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models_vault import VaultDocument
from app.repositories.vault_repository import VaultRepository
from app.schemas_vault import (
    VaultActivityAction,
    VaultArchiveFormMeta,
    VaultArchiveStatus,
    VaultDocumentDetail,
    VaultDocumentListItem,
    VaultDocumentListResponse,
    VaultDocumentResponse,
    VaultDocumentType,
    VaultDownloadUrlResponse,
    VaultPagination,
    VaultSortBy,
    VaultSortOrder,
)
from app.services.vault.checksum_service import calculate_sha256
from app.services.vault.exceptions import (
    VaultDatabaseError,
    VaultDuplicateDocumentError,
    VaultFileTooLargeError,
    VaultInvalidFileError,
    VaultNotFoundError,
    VaultStorageError,
    VaultValidationError,
)
from app.services.vault.storage_service import VaultStorageService, build_storage_path
from app.services.vault.vault_access_service import (
    DOCUMENT_NOT_FOUND_MESSAGE,
    assert_can_archive,
    assert_can_read,
)

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


def _to_list_item(doc: VaultDocument) -> VaultDocumentListItem:
    return VaultDocumentListItem(
        id=doc.id,
        tenant_id=doc.organization_id,
        document_type=VaultDocumentType(doc.document_type),
        document_number=doc.document_number,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        invoice_date=doc.invoice_date,
        due_date=doc.due_date,
        amount_ht=doc.amount_ht,
        amount_vat=doc.amount_vat,
        amount_ttc=doc.amount_ttc,
        currency=doc.currency,
        archive_status=doc.archive_status,  # type: ignore[arg-type]
        accounting_status=doc.accounting_status,  # type: ignore[arg-type]
        email_status=doc.email_status,  # type: ignore[arg-type]
        version=doc.version,
        archived_at=doc.archived_at,
        created_at=doc.created_at,
    )


def _to_detail(doc: VaultDocument) -> VaultDocumentDetail:
    return VaultDocumentDetail(
        id=doc.id,
        tenant_id=doc.organization_id,
        document_type=VaultDocumentType(doc.document_type),
        document_number=doc.document_number,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        invoice_date=doc.invoice_date,
        due_date=doc.due_date,
        amount_ht=doc.amount_ht,
        amount_vat=doc.amount_vat,
        amount_ttc=doc.amount_ttc,
        currency=doc.currency,
        archive_status=doc.archive_status,  # type: ignore[arg-type]
        accounting_status=doc.accounting_status,  # type: ignore[arg-type]
        email_status=doc.email_status,  # type: ignore[arg-type]
        version=doc.version,
        is_locked=False,
        archived_at=doc.archived_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def list_documents(
    db: Session,
    *,
    user_id: int,
    organization_id: int,
    page: int = 1,
    page_size: int = 20,
    document_type: VaultDocumentType | None = None,
    archive_status: VaultArchiveStatus | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: VaultSortBy = VaultSortBy.created_at,
    sort_order: VaultSortOrder = VaultSortOrder.desc,
) -> VaultDocumentListResponse:
    assert_can_read(db, user_id=user_id, organization_id=organization_id)
    if page < 1 or page_size < 1 or page_size > 100:
        raise VaultValidationError("Paramètres de pagination invalides")

    repo = VaultRepository(db)
    total = repo.count_documents(
        organization_id=organization_id,
        document_type=document_type,
        archive_status=archive_status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    rows = repo.list_documents(
        organization_id=organization_id,
        page=page,
        page_size=page_size,
        document_type=document_type,
        archive_status=archive_status,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return VaultDocumentListResponse(
        items=[_to_list_item(r) for r in rows],
        pagination=VaultPagination(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


def get_document_details(
    db: Session,
    *,
    user_id: int,
    organization_id: int,
    document_id: str,
) -> VaultDocumentDetail:
    assert_can_read(db, user_id=user_id, organization_id=organization_id)
    repo = VaultRepository(db)
    doc = repo.get_document_for_tenant(
        document_id=document_id, organization_id=organization_id
    )
    if not doc or doc.archive_status == VaultArchiveStatus.deleted.value:
        raise VaultNotFoundError(DOCUMENT_NOT_FOUND_MESSAGE)

    try:
        repo.create_activity_log(
            organization_id=organization_id,
            document_id=doc.id,
            user_id=user_id,
            action=VaultActivityAction.document_viewed,
            metadata={"document_id": doc.id, "source": "vault_document_details"},
        )
    except Exception:
        logger.exception(
            "vault_view_log_failed",
            extra={"document_id": doc.id, "organization_id": organization_id},
        )

    return _to_detail(doc)


def create_download_url(
    db: Session,
    *,
    user_id: int,
    organization_id: int,
    document_id: str,
    expires_in: int | None = None,
    storage: VaultStorageService | None = None,
) -> VaultDownloadUrlResponse:
    assert_can_read(db, user_id=user_id, organization_id=organization_id)
    repo = VaultRepository(db)
    doc = repo.get_document_for_tenant(
        document_id=document_id, organization_id=organization_id
    )
    if not doc or doc.archive_status == VaultArchiveStatus.deleted.value:
        raise VaultNotFoundError(DOCUMENT_NOT_FOUND_MESSAGE)

    ttl = expires_in if expires_in is not None else settings.elfis_vault_signed_url_ttl_seconds
    ttl = max(60, min(900, int(ttl)))

    storage_svc = storage or VaultStorageService()
    # Ne jamais logger l'URL signée
    download_url = storage_svc.create_signed_download_url(
        storage_path=doc.storage_path,
        expires_in=ttl,
    )
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    try:
        repo.create_activity_log(
            organization_id=organization_id,
            document_id=doc.id,
            user_id=user_id,
            action=VaultActivityAction.document_downloaded,
            metadata={
                "document_id": doc.id,
                "expires_in": ttl,
                "source": "vault_download_url",
            },
        )
    except Exception:
        logger.exception(
            "vault_download_log_failed",
            extra={"document_id": doc.id, "organization_id": organization_id},
        )

    return VaultDownloadUrlResponse(
        document_id=doc.id,
        download_url=download_url,
        expires_in=ttl,
        expires_at=expires_at,
    )
