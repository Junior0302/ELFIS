"""Migration progressive StorageObject local → distant."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.storage.storage_exceptions import StorageProviderError, StorageValidationError
from app.storage.storage_metadata import sanitize_document_metadata
from app.storage.storage_models import ElfisStorageMigration, ElfisStorageObject
from app.storage.storage_provider import StorageProvider
from app.storage.storage_registry import build_storage_provider
from app.storage.storage_types import StorageObjectStatus

logger = logging.getLogger(__name__)

_ACTIVE = frozenset({"pending", "copying", "copied", "verified"})


class StorageMigrationService:
    """
    Fallback lecture source : uniquement si migration status in {copied, verified}
    et cible introuvable — jamais permanent/silencieux.
    """

    def __init__(
        self,
        db: Session,
        *,
        source: StorageProvider | None = None,
        target: StorageProvider | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._db = db
        self._source = source
        self._target = target
        self._audit = audit_logger

    def list_migrations(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ElfisStorageMigration], int]:
        q = self._db.query(ElfisStorageMigration)
        if status:
            q = q.filter(ElfisStorageMigration.status == status)
        total = q.count()
        items = (
            q.order_by(ElfisStorageMigration.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 200)))
            .all()
        )
        return items, int(total)

    def get(self, migration_id: str) -> ElfisStorageMigration | None:
        return self._db.get(ElfisStorageMigration, migration_id)

    def preview_candidates(
        self,
        *,
        from_provider: str = "local",
        organization_id: int | None = None,
        document_id: str | None = None,
        limit: int = 50,
    ) -> list[ElfisStorageObject]:
        q = self._db.query(ElfisStorageObject).filter(
            ElfisStorageObject.provider == from_provider,
            ElfisStorageObject.status.in_(
                [
                    StorageObjectStatus.AVAILABLE.value,
                    StorageObjectStatus.QUARANTINED.value,
                ]
            ),
        )
        if organization_id is not None:
            q = q.filter(ElfisStorageObject.organization_id == organization_id)
        if document_id:
            from app.storage.storage_models import ElfisDocumentRecord

            q = q.join(
                ElfisDocumentRecord,
                ElfisDocumentRecord.current_storage_object_id == ElfisStorageObject.id,
            ).filter(ElfisDocumentRecord.id == document_id)
        return q.order_by(ElfisStorageObject.created_at.asc()).limit(limit).all()

    def migrate_one(
        self,
        obj: ElfisStorageObject,
        *,
        to_provider: str = "supabase",
        verify_checksum: bool = True,
        delete_source_after_verify: bool = False,
        keep_source: bool = True,
        actor_user_id: int | None = None,
        dry_run: bool = True,
    ) -> ElfisStorageMigration:
        source = self._source or build_storage_provider(obj.provider)
        target = self._target or build_storage_provider(to_provider)
        if target.name == "disabled":
            raise StorageValidationError("target_disabled", "Provider cible indisponible")

        existing = (
            self._db.query(ElfisStorageMigration)
            .filter(
                ElfisStorageMigration.storage_object_id == obj.id,
                ElfisStorageMigration.status.in_(list(_ACTIVE)),
            )
            .first()
        )
        if existing and existing.status == "switched":
            return existing

        target_ns = (
            getattr(settings, "supabase_storage_document_namespace", None) or "documents"
            if to_provider == "supabase"
            else obj.namespace
        )
        if obj.status == StorageObjectStatus.QUARANTINED.value:
            target_ns = getattr(settings, "supabase_storage_quarantine_namespace", None) or "quarantine"
        target_key = obj.object_key
        if to_provider == "supabase" and not target_key.startswith(f"{obj.organization_id or 0}/"):
            from app.storage.providers.supabase_storage_provider import build_document_object_key

            target_key = build_document_object_key(
                organization_id=obj.organization_id,
                storage_object_id=obj.id,
                extension=obj.extension or "",
            )
            if target_key.startswith("documents/"):
                target_key = target_key[len("documents/") :]

        mig = existing or ElfisStorageMigration(
            id=str(uuid4()),
            storage_object_id=obj.id,
            source_provider=obj.provider,
            source_namespace=obj.namespace,
            source_object_key=obj.object_key,
            target_provider=to_provider,
            target_namespace=target_ns,
            target_object_key=target_key,
            status="pending",
            created_by_user_id=actor_user_id,
        )
        if not existing:
            self._db.add(mig)
            self._db.flush()

        if dry_run:
            self._db.rollback()
            mig.status = "pending"
            return mig

        mig.status = "copying"
        mig.started_at = datetime.utcnow()
        self._db.commit()
        self._safe_audit("record_storage_migration_started", migration_id=mig.id, storage_object_id=obj.id)

        try:
            if not source.object_exists(namespace=obj.namespace, object_key=obj.object_key):
                raise StorageProviderError("source_missing", "Objet source absent")

            hasher = hashlib.sha256()
            size = 0
            with source.open_stream(namespace=obj.namespace, object_key=obj.object_key) as fh:
                # write to OS temp then put_stream — évite charger en RAM
                import tempfile
                import os
                from pathlib import Path

                fd, tmp_name = tempfile.mkstemp(prefix="elfis_mig_")
                try:
                    with os.fdopen(fd, "wb") as out:
                        while True:
                            chunk = fh.read(65536)
                            if not chunk:
                                break
                            hasher.update(chunk)
                            size += len(chunk)
                            out.write(chunk)
                    path = Path(tmp_name)
                    with path.open("rb") as inp:
                        target.put_stream(
                            namespace=target_ns,
                            object_key=target_key,
                            stream=inp,
                            size_bytes=size,
                            content_type=obj.mime_type_detected or obj.mime_type_declared,
                            metadata={"checksum_sha256": hasher.hexdigest()},
                            overwrite=False,
                        )
                finally:
                    try:
                        os.unlink(tmp_name)
                    except OSError:
                        pass

            mig.status = "copied"
            self._db.commit()
            self._safe_audit(
                "record_storage_migration_object_copied",
                migration_id=mig.id,
                storage_object_id=obj.id,
            )

            checksum_ok = True
            if verify_checksum and obj.checksum_sha256:
                checksum_ok = hasher.hexdigest().lower() == obj.checksum_sha256.lower()
            if not target.object_exists(namespace=target_ns, object_key=target_key):
                raise StorageProviderError("target_missing", "Objet cible absent après copie")
            meta = target.get_metadata(namespace=target_ns, object_key=target_key)
            if meta.size_bytes and obj.size_bytes and int(meta.size_bytes) != int(obj.size_bytes):
                # size may be 0 if listing incomplete — warn only if both known
                if meta.size_bytes > 0:
                    raise StorageProviderError("size_mismatch", "Taille cible incohérente")

            mig.checksum_verified = bool(checksum_ok)
            mig.verified_at = datetime.utcnow()
            mig.status = "verified"
            self._db.commit()
            self._safe_audit(
                "record_storage_migration_object_verified",
                migration_id=mig.id,
                storage_object_id=obj.id,
                checksum_verified=checksum_ok,
            )
            if not checksum_ok and verify_checksum:
                raise StorageProviderError("checksum_mismatch", "Checksum non vérifié")

            # switch
            obj.provider = to_provider
            obj.namespace = target_ns
            obj.object_key = target_key
            obj.updated_at = datetime.utcnow()
            mig.status = "switched"
            mig.completed_at = datetime.utcnow()
            self._db.commit()
            self._safe_audit(
                "record_storage_migration_object_switched",
                migration_id=mig.id,
                storage_object_id=obj.id,
            )

            if delete_source_after_verify and not keep_source:
                try:
                    source.delete_object(
                        namespace=mig.source_namespace, object_key=mig.source_object_key
                    )
                    mig.source_deleted_at = datetime.utcnow()
                    self._db.commit()
                except Exception:
                    logger.warning(
                        "migration_source_delete_failed",
                        extra={"migration_id": mig.id, "storage_object_id": obj.id},
                    )
            return mig
        except Exception as exc:
            self._db.rollback()
            mig = self._db.get(ElfisStorageMigration, mig.id) or mig
            mig.status = "failed"
            mig.error_code = getattr(exc, "code", type(exc).__name__)[:64]
            mig.updated_at = datetime.utcnow()
            self._db.commit()
            self._safe_audit(
                "record_storage_migration_failed",
                migration_id=mig.id,
                storage_object_id=obj.id,
                error_code=mig.error_code,
            )
            raise

    def resolve_read_provider(self, obj: ElfisStorageObject) -> tuple[StorageProvider, str, str]:
        """
        Lecture : provider courant.
        Fallback source uniquement si migration verified/copied non switched et cible absente.
        """
        primary = build_storage_provider(obj.provider)
        if primary.object_exists(namespace=obj.namespace, object_key=obj.object_key):
            return primary, obj.namespace, obj.object_key

        mig = (
            self._db.query(ElfisStorageMigration)
            .filter(
                ElfisStorageMigration.storage_object_id == obj.id,
                ElfisStorageMigration.status.in_(["copied", "verified", "switched"]),
            )
            .order_by(ElfisStorageMigration.created_at.desc())
            .first()
        )
        if mig and mig.status in {"copied", "verified"}:
            source = build_storage_provider(mig.source_provider)
            if source.object_exists(
                namespace=mig.source_namespace, object_key=mig.source_object_key
            ):
                logger.warning(
                    "storage_migration_fallback_read",
                    extra={"storage_object_id": obj.id, "migration_id": mig.id},
                )
                return source, mig.source_namespace, mig.source_object_key
        return primary, obj.namespace, obj.object_key

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**kwargs)
        except Exception:
            logger.debug("migration_audit_failed", exc_info=True)
