"""Repository SQLAlchemy pour ELFIS Vault."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models_vault import VaultActivityLog, VaultDocument
from app.schemas_vault import VaultActivityAction, VaultArchiveStatus, VaultDocumentType
from app.services.vault.exceptions import VaultDatabaseError

logger = logging.getLogger(__name__)


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
            email_status="not_sent",
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
        # Ne jamais stocker secrets / contenu PDF
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
        return (
            self._db.query(VaultDocument)
            .filter(
                VaultDocument.id == document_id,
                VaultDocument.organization_id == organization_id,
            )
            .first()
        )
