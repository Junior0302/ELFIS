"""Repositories Storage / Document Registry / Versions / Legal Hold."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.storage.storage_models import (
    ElfisDocumentLegalHold,
    ElfisDocumentLink,
    ElfisDocumentRecord,
    ElfisDocumentTombstone,
    ElfisDocumentVersion,
    ElfisStorageObject,
)
from app.storage.storage_types import DocumentStatus, StorageObjectStatus


class StorageObjectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, row: ElfisStorageObject, *, commit: bool = False) -> ElfisStorageObject:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def get(self, object_id: str) -> ElfisStorageObject | None:
        return self._db.get(ElfisStorageObject, object_id)

    def find_by_org_checksum(
        self,
        organization_id: int,
        checksum_sha256: str,
        *,
        exclude_id: str | None = None,
    ) -> ElfisStorageObject | None:
        if not checksum_sha256:
            return None
        q = self._db.query(ElfisStorageObject).filter(
            ElfisStorageObject.organization_id == organization_id,
            ElfisStorageObject.checksum_sha256 == checksum_sha256,
            ElfisStorageObject.status != StorageObjectStatus.DELETED.value,
            ElfisStorageObject.status != StorageObjectStatus.PURGED.value,
        )
        if exclude_id:
            q = q.filter(ElfisStorageObject.id != exclude_id)
        return q.order_by(ElfisStorageObject.created_at.desc()).first()

    def count_version_refs(self, storage_object_id: str) -> int:
        return (
            self._db.query(func.count(ElfisDocumentVersion.id))
            .filter(
                ElfisDocumentVersion.storage_object_id == storage_object_id,
                ElfisDocumentVersion.status != "purged",
            )
            .scalar()
            or 0
        )

    def mark_deleted(self, object_id: str, *, commit: bool = False) -> bool:
        row = self.get(object_id)
        if not row:
            return False
        row.status = StorageObjectStatus.DELETED.value
        row.deleted_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
        else:
            self._db.flush()
        return True

    def mark_purged(self, object_id: str, *, commit: bool = False) -> bool:
        row = self.get(object_id)
        if not row:
            return False
        row.status = StorageObjectStatus.PURGED.value
        row.deleted_at = row.deleted_at or datetime.utcnow()
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
        else:
            self._db.flush()
        return True


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, row: ElfisDocumentRecord, *, commit: bool = False) -> ElfisDocumentRecord:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def get(self, document_id: str) -> ElfisDocumentRecord | None:
        return self._db.get(ElfisDocumentRecord, document_id)

    def lock_for_update(self, document_id: str) -> ElfisDocumentRecord | None:
        """Verrou pessimiste PostgreSQL ; SQLite ignore with_for_update."""
        q = self._db.query(ElfisDocumentRecord).filter(ElfisDocumentRecord.id == document_id)
        try:
            return q.with_for_update().first()
        except Exception:
            return q.first()

    def list_for_organization(
        self,
        organization_id: int,
        *,
        include_archived: bool = False,
        include_deleted: bool = False,
        document_type: str | None = None,
        source: str | None = None,
        status: str | None = None,
        product: str | None = None,
        filename_contains: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ElfisDocumentRecord], int]:
        q = self._db.query(ElfisDocumentRecord).filter(
            ElfisDocumentRecord.organization_id == organization_id
        )
        if status:
            q = q.filter(ElfisDocumentRecord.status == status)
        else:
            if not include_deleted:
                q = q.filter(ElfisDocumentRecord.status != DocumentStatus.DELETED.value)
                q = q.filter(ElfisDocumentRecord.status != DocumentStatus.PURGED.value)
            if not include_archived:
                q = q.filter(ElfisDocumentRecord.status != DocumentStatus.ARCHIVED.value)
        if document_type:
            q = q.filter(ElfisDocumentRecord.document_type == document_type[:64])
        if source:
            q = q.filter(ElfisDocumentRecord.source == source[:32])
        if product:
            q = q.filter(ElfisDocumentRecord.product == product[:64])
        if filename_contains:
            like = f"%{filename_contains[:100]}%"
            q = q.join(
                ElfisStorageObject,
                ElfisDocumentRecord.current_storage_object_id == ElfisStorageObject.id,
            ).filter(ElfisStorageObject.safe_filename.ilike(like))
        if entity_type and entity_id:
            q = q.join(ElfisDocumentLink, ElfisDocumentLink.document_id == ElfisDocumentRecord.id).filter(
                ElfisDocumentLink.entity_type == entity_type[:64],
                ElfisDocumentLink.entity_id == str(entity_id)[:128],
            )
        total = q.count()
        items = (
            q.order_by(ElfisDocumentRecord.created_at.desc(), ElfisDocumentRecord.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return items, int(total)

    def archive(self, document_id: str, *, commit: bool = False) -> ElfisDocumentRecord | None:
        row = self.get(document_id)
        if not row:
            return None
        row.status = DocumentStatus.ARCHIVED.value
        row.archived_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row

    def unarchive(self, document_id: str, *, commit: bool = False) -> ElfisDocumentRecord | None:
        row = self.get(document_id)
        if not row:
            return None
        row.status = DocumentStatus.AVAILABLE.value
        row.archived_at = None
        row.updated_at = datetime.utcnow()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()
        return row


class DocumentVersionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, row: ElfisDocumentVersion, *, commit: bool = False) -> ElfisDocumentVersion:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def get(self, version_id: str) -> ElfisDocumentVersion | None:
        return self._db.get(ElfisDocumentVersion, version_id)

    def list_for_document(self, document_id: str) -> list[ElfisDocumentVersion]:
        return (
            self._db.query(ElfisDocumentVersion)
            .filter(ElfisDocumentVersion.document_id == document_id)
            .order_by(ElfisDocumentVersion.version_number.desc())
            .all()
        )

    def max_version_number(self, document_id: str) -> int:
        val = (
            self._db.query(func.max(ElfisDocumentVersion.version_number))
            .filter(ElfisDocumentVersion.document_id == document_id)
            .scalar()
        )
        return int(val or 0)

    def get_by_document_and_number(
        self, document_id: str, version_number: int
    ) -> ElfisDocumentVersion | None:
        return (
            self._db.query(ElfisDocumentVersion)
            .filter(
                ElfisDocumentVersion.document_id == document_id,
                ElfisDocumentVersion.version_number == version_number,
            )
            .first()
        )


class DocumentLinkRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, row: ElfisDocumentLink, *, commit: bool = False) -> ElfisDocumentLink:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def list_for_document(self, document_id: str) -> list[ElfisDocumentLink]:
        return (
            self._db.query(ElfisDocumentLink)
            .filter(ElfisDocumentLink.document_id == document_id)
            .order_by(ElfisDocumentLink.created_at.asc())
            .all()
        )

    def find_existing(
        self,
        *,
        document_id: str,
        entity_type: str,
        entity_id: str,
        relation_type: str,
    ) -> ElfisDocumentLink | None:
        return (
            self._db.query(ElfisDocumentLink)
            .filter(
                ElfisDocumentLink.document_id == document_id,
                ElfisDocumentLink.entity_type == entity_type,
                ElfisDocumentLink.entity_id == entity_id,
                ElfisDocumentLink.relation_type == relation_type,
            )
            .first()
        )


class LegalHoldRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, row: ElfisDocumentLegalHold, *, commit: bool = False) -> ElfisDocumentLegalHold:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def get(self, hold_id: str) -> ElfisDocumentLegalHold | None:
        return self._db.get(ElfisDocumentLegalHold, hold_id)

    def list_for_document(self, document_id: str, *, active_only: bool = False) -> list[ElfisDocumentLegalHold]:
        q = self._db.query(ElfisDocumentLegalHold).filter(
            ElfisDocumentLegalHold.document_id == document_id
        )
        if active_only:
            q = q.filter(ElfisDocumentLegalHold.active.is_(True))
        return q.order_by(ElfisDocumentLegalHold.placed_at.desc()).all()

    def has_active(self, document_id: str) -> bool:
        return (
            self._db.query(ElfisDocumentLegalHold.id)
            .filter(
                ElfisDocumentLegalHold.document_id == document_id,
                ElfisDocumentLegalHold.active.is_(True),
            )
            .first()
            is not None
        )


class TombstoneRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, row: ElfisDocumentTombstone, *, commit: bool = False) -> ElfisDocumentTombstone:
        self._db.add(row)
        self._db.flush()
        if commit:
            self._db.commit()
            self._db.refresh(row)
        return row

    def get_by_document(self, document_id: str) -> ElfisDocumentTombstone | None:
        return (
            self._db.query(ElfisDocumentTombstone)
            .filter(ElfisDocumentTombstone.document_id == document_id)
            .first()
        )
