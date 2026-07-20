"""Repository SQLAlchemy pour ELFIS Vault."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.models_vault import VaultActivityLog, VaultDocument
from app.schemas_vault import (
    VaultActivityAction,
    VaultArchiveStatus,
    VaultDocumentType,
    VaultSortBy,
    VaultSortOrder,
)
from app.services.vault.exceptions import VaultDatabaseError

logger = logging.getLogger(__name__)

_SORT_COLUMNS = {
    VaultSortBy.created_at: VaultDocument.created_at,
    VaultSortBy.invoice_date: VaultDocument.invoice_date,
    VaultSortBy.document_number: VaultDocument.document_number,
    VaultSortBy.amount_ttc: VaultDocument.amount_ttc,
}


class VaultRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_duplicate(
        self, *, organization_id: int, checksum_sha256: str
    ) -> VaultDocument | None:
        return (
            self._db.query(VaultDocument)
            .filter(
                VaultDocument.organization_id == organization_id,
                VaultDocument.checksum_sha256 == checksum_sha256,
                VaultDocument.archive_status != VaultArchiveStatus.deleted.value,
            )
            .first()
        )

    def create_document(
        self,
        *,
        organization_id: int,
        document_type: VaultDocumentType,
        document_number: str | None,
        original_filename: str,
        storage_path: str,
        mime_type: str,
        file_size: int,
        checksum_sha256: str,
        invoice_date: Any = None,
        due_date: Any = None,
        amount_ht: Decimal | None = None,
        amount_vat: Decimal | None = None,
        amount_ttc: Decimal | None = None,
        currency: str = "EUR",
        customer_id: int | None = None,
        supplier_id: int | None = None,
        archived_by_user_id: int | None = None,
        email_status: str = "not_sent",
    ) -> VaultDocument:
        now = datetime.utcnow()
        doc = VaultDocument(
            organization_id=organization_id,
            document_type=document_type.value,
            document_number=document_number,
            original_filename=original_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=file_size,
            checksum_sha256=checksum_sha256,
            invoice_date=invoice_date,
            due_date=due_date,
            amount_ht=amount_ht,
            amount_vat=amount_vat,
            amount_ttc=amount_ttc,
            currency=currency,
            customer_id=customer_id,
            supplier_id=supplier_id,
            archive_status=VaultArchiveStatus.archived.value,
            accounting_status="not_processed",
            email_status=email_status,
            version=1,
            archived_by_user_id=archived_by_user_id,
            archived_at=now,
            created_at=now,
            updated_at=now,
        )
        try:
            self._db.add(doc)
            self._db.commit()
            self._db.refresh(doc)
        except Exception as exc:
            self._db.rollback()
            logger.exception("vault_create_document_failed")
            raise VaultDatabaseError("Échec d'enregistrement du document") from exc
        return doc

    def create_activity_log(
        self,
        *,
        organization_id: int,
        document_id: str,
        user_id: int | None,
        action: VaultActivityAction,
        metadata: dict[str, Any],
    ) -> VaultActivityLog:
        safe_meta = {
            k: v
            for k, v in metadata.items()
            if k
            not in {
                "password",
                "token",
                "api_key",
                "service_role_key",
                "content",
                "pdf_bytes",
                "iban",
                "bic",
                "download_url",
                "signed_url",
            }
        }
        log = VaultActivityLog(
            organization_id=organization_id,
            document_id=document_id,
            user_id=user_id,
            action=action.value,
            metadata_json=json.dumps(safe_meta, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )
        try:
            self._db.add(log)
            self._db.commit()
            self._db.refresh(log)
        except Exception as exc:
            self._db.rollback()
            logger.exception("vault_create_activity_log_failed")
            raise VaultDatabaseError("Échec d'enregistrement du journal") from exc
        return log

    def get_document(self, *, document_id: str, organization_id: int) -> VaultDocument | None:
        return self.get_document_for_tenant(
            document_id=document_id, organization_id=organization_id
        )

    def get_document_by_id(self, *, document_id: str) -> VaultDocument | None:
        return self._db.query(VaultDocument).filter(VaultDocument.id == document_id).first()

    def get_document_for_tenant(
        self, *, document_id: str, organization_id: int
    ) -> VaultDocument | None:
        return (
            self._db.query(VaultDocument)
            .filter(
                VaultDocument.id == document_id,
                VaultDocument.organization_id == organization_id,
            )
            .first()
        )

    def update_email_status(
        self, *, document_id: str, organization_id: int, email_status: str
    ) -> VaultDocument | None:
        doc = self.get_document_for_tenant(
            document_id=document_id, organization_id=organization_id
        )
        if not doc:
            return None
        doc.email_status = email_status
        doc.updated_at = datetime.utcnow()
        try:
            self._db.add(doc)
            self._db.commit()
            self._db.refresh(doc)
        except Exception as exc:
            self._db.rollback()
            logger.exception("vault_update_email_status_failed")
            raise VaultDatabaseError("Échec de mise à jour du statut e-mail") from exc
        return doc

    def _list_filters(
        self,
        *,
        organization_id: int,
        document_type: VaultDocumentType | None,
        archive_status: VaultArchiveStatus | None,
        search: str | None,
        date_from: date | None,
        date_to: date | None,
    ):
        q = self._db.query(VaultDocument).filter(
            VaultDocument.organization_id == organization_id,
            VaultDocument.archive_status != VaultArchiveStatus.deleted.value,
        )
        if document_type is not None:
            q = q.filter(VaultDocument.document_type == document_type.value)
        if archive_status is not None:
            q = q.filter(VaultDocument.archive_status == archive_status.value)
        if date_from is not None:
            q = q.filter(VaultDocument.invoice_date >= date_from)
        if date_to is not None:
            q = q.filter(VaultDocument.invoice_date <= date_to)
        if search:
            term = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    VaultDocument.document_number.ilike(term),
                    VaultDocument.original_filename.ilike(term),
                    VaultDocument.storage_path.ilike(term),
                )
            )
        return q

    def count_documents(
        self,
        *,
        organization_id: int,
        document_type: VaultDocumentType | None = None,
        archive_status: VaultArchiveStatus | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        q = self._list_filters(
            organization_id=organization_id,
            document_type=document_type,
            archive_status=archive_status,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        return int(q.with_entities(func.count(VaultDocument.id)).scalar() or 0)

    def list_documents(
        self,
        *,
        organization_id: int,
        page: int,
        page_size: int,
        document_type: VaultDocumentType | None = None,
        archive_status: VaultArchiveStatus | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort_by: VaultSortBy = VaultSortBy.created_at,
        sort_order: VaultSortOrder = VaultSortOrder.desc,
    ) -> list[VaultDocument]:
        q = self._list_filters(
            organization_id=organization_id,
            document_type=document_type,
            archive_status=archive_status,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        col = _SORT_COLUMNS.get(sort_by, VaultDocument.created_at)
        order_fn = asc if sort_order == VaultSortOrder.asc else desc
        q = q.order_by(order_fn(col), desc(VaultDocument.id))
        offset = (page - 1) * page_size
        return q.offset(offset).limit(page_size).all()
