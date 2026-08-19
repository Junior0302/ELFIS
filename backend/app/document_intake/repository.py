"""Repository Document Intake."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.document_intake.enums import IntakeItemStatus
from app.document_intake.models import ElfisDocumentIntakeItem


class DocumentIntakeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, item_id: str) -> ElfisDocumentIntakeItem | None:
        return self._db.get(ElfisDocumentIntakeItem, item_id)

    def get_for_org(self, item_id: str, organization_id: int) -> ElfisDocumentIntakeItem | None:
        row = self.get(item_id)
        if not row or row.organization_id != organization_id:
            return None
        return row

    def get_by_universal_document_id(
        self, organization_id: int, universal_document_id: str
    ) -> ElfisDocumentIntakeItem | None:
        return (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.universal_document_id == universal_document_id)
            .first()
        )

    def find_by_idempotency_key(
        self, *, organization_id: int, idempotency_key: str
    ) -> ElfisDocumentIntakeItem | None:
        if not idempotency_key:
            return None
        return (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.idempotency_key == idempotency_key)
            .order_by(ElfisDocumentIntakeItem.created_at.asc())
            .first()
        )

    def add(self, row: ElfisDocumentIntakeItem, *, commit: bool = True) -> ElfisDocumentIntakeItem:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def save(self, row: ElfisDocumentIntakeItem, *, commit: bool = True) -> ElfisDocumentIntakeItem:
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def list_items(
        self,
        *,
        organization_id: int,
        migration_session_id: str | None = None,
        upload_session_id: str | None = None,
        batch_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ElfisDocumentIntakeItem], int]:
        q = self._db.query(ElfisDocumentIntakeItem).filter(
            ElfisDocumentIntakeItem.organization_id == organization_id
        )
        if migration_session_id:
            q = q.filter(ElfisDocumentIntakeItem.migration_session_id == migration_session_id)
        if upload_session_id:
            q = q.filter(ElfisDocumentIntakeItem.upload_session_id == upload_session_id)
        if batch_id:
            q = q.filter(ElfisDocumentIntakeItem.batch_id == batch_id)
        if status:
            q = q.filter(ElfisDocumentIntakeItem.status == status)
        total = q.count()
        items = (
            q.order_by(ElfisDocumentIntakeItem.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
            .all()
        )
        return items, int(total)

    def find_by_checksum(
        self, *, organization_id: int, checksum_sha256: str
    ) -> ElfisDocumentIntakeItem | None:
        return (
            self._db.query(ElfisDocumentIntakeItem)
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.checksum_sha256 == checksum_sha256)
            .filter(
                ElfisDocumentIntakeItem.status.notin_(
                    [IntakeItemStatus.REJECTED.value, IntakeItemStatus.CANCELLED.value]
                )
            )
            .order_by(ElfisDocumentIntakeItem.created_at.asc())
            .first()
        )

    def count_for_session(self, *, organization_id: int, migration_session_id: str) -> int:
        return (
            self._db.query(func.count(ElfisDocumentIntakeItem.id))
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(ElfisDocumentIntakeItem.migration_session_id == migration_session_id)
            .filter(
                ElfisDocumentIntakeItem.status.notin_(
                    [IntakeItemStatus.REJECTED.value, IntakeItemStatus.CANCELLED.value]
                )
            )
            .scalar()
            or 0
        )

    def sum_bytes_for_org(self, organization_id: int) -> int:
        val = (
            self._db.query(func.coalesce(func.sum(ElfisDocumentIntakeItem.size_bytes), 0))
            .filter(ElfisDocumentIntakeItem.organization_id == organization_id)
            .filter(
                ElfisDocumentIntakeItem.status.notin_(
                    [IntakeItemStatus.REJECTED.value, IntakeItemStatus.CANCELLED.value]
                )
            )
            .scalar()
        )
        return int(val or 0)
