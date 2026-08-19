"""Service métier — Document Intake Engine (Sprint 2 + 2.5)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.document_intake.analytics_service import UploadAnalyticsService
from app.document_intake.doc_id import allocate_universal_document_id
from app.document_intake.enums import (
    DEFAULT_MAX_BYTES_PER_ORG,
    DEFAULT_MAX_BYTES_PER_USER_BATCH,
    DEFAULT_MAX_FILES_PER_BATCH,
    DEFAULT_MAX_FILES_PER_SESSION,
    DocumentLifecycleStatus,
    DuplicateType,
    IntakeItemStatus,
    IntakeOrigin,
    LifecycleActorType,
)
from app.document_intake.events import publish_intake_event
from app.document_intake.exceptions import (
    DocumentIntakeNotFoundError,
    DocumentIntakeQuotaError,
    DocumentIntakeValidationError,
)
from app.document_intake.fingerprint import FileFingerprintService
from app.document_intake.format_registry import list_formats
from app.document_intake.inventory import inventory_summary
from app.document_intake.lifecycle_service import DocumentLifecycleService
from app.document_intake.models import ElfisDocumentIntakeItem, ElfisDocumentUploadSession
from app.document_intake.repository import DocumentIntakeRepository
from app.document_intake.scanner import IntakeScanner
from app.document_intake.storage import get_storage_provider
from app.document_intake.upload_session_service import UploadSessionService
from app.document_intake.validators import validate_content
from app.migration_center.activity_service import MigrationActivityService

logger = logging.getLogger(__name__)


class DocumentIntakeService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = DocumentIntakeRepository(db)
        self._scanner = IntakeScanner()
        self._lifecycle = DocumentLifecycleService(db)
        self._fingerprint = FileFingerprintService()
        self._upload_sessions = UploadSessionService(db)
        self._analytics = UploadAnalyticsService(db)
        self._activity = MigrationActivityService(db)
        self._storage = get_storage_provider()

    def get_format_catalog(self) -> list[dict]:
        return list_formats()

    def get_for_org(self, item_id: str, organization_id: int) -> ElfisDocumentIntakeItem:
        row = self._repo.get_for_org(item_id, organization_id)
        if not row:
            raise DocumentIntakeNotFoundError("not_found", "Fichier introuvable")
        return row

    def get_by_universal_document_id(
        self, organization_id: int, universal_document_id: str
    ) -> ElfisDocumentIntakeItem:
        row = self._repo.get_by_universal_document_id(organization_id, universal_document_id)
        if not row:
            raise DocumentIntakeNotFoundError("not_found", "Fichier introuvable")
        return row

    def list_lifecycle(
        self, item_id: str, organization_id: int
    ) -> list:
        self.get_for_org(item_id, organization_id)
        return self._lifecycle.list_entries(
            organization_id=organization_id, document_intake_item_id=item_id
        )

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
    ) -> tuple[list[ElfisDocumentIntakeItem], int, dict[str, Any]]:
        items, total = self._repo.list_items(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            upload_session_id=upload_session_id,
            batch_id=batch_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        summary = inventory_summary(
            self._db,
            organization_id=organization_id,
            migration_session_id=migration_session_id,
        )
        return items, total, summary

    def _assert_quotas(
        self,
        *,
        organization_id: int,
        migration_session_id: str | None,
        incoming_count: int,
        incoming_bytes: int,
    ) -> None:
        if incoming_count > DEFAULT_MAX_FILES_PER_BATCH:
            raise DocumentIntakeQuotaError(
                "batch_file_limit",
                f"Trop de fichiers dans le lot (max {DEFAULT_MAX_FILES_PER_BATCH})",
            )
        if incoming_bytes > DEFAULT_MAX_BYTES_PER_USER_BATCH:
            raise DocumentIntakeQuotaError(
                "batch_byte_limit",
                "Taille cumulée du lot dépassée",
            )
        org_bytes = self._repo.sum_bytes_for_org(organization_id)
        if org_bytes + incoming_bytes > DEFAULT_MAX_BYTES_PER_ORG:
            raise DocumentIntakeQuotaError(
                "org_storage_quota",
                "Quota organisation dépassé",
            )
        if migration_session_id:
            n = self._repo.count_for_session(
                organization_id=organization_id,
                migration_session_id=migration_session_id,
            )
            if n + incoming_count > DEFAULT_MAX_FILES_PER_SESSION:
                raise DocumentIntakeQuotaError(
                    "session_file_limit",
                    f"Trop de fichiers pour cette session (max {DEFAULT_MAX_FILES_PER_SESSION})",
                )

    def ingest_bytes(
        self,
        *,
        organization_id: int,
        filename: str,
        content: bytes,
        actor_user_id: int | None,
        declared_mime: str | None = None,
        migration_session_id: str | None = None,
        relative_path: str | None = None,
        batch_id: str | None = None,
        origin: str = IntakeOrigin.API.value,
        upload_session_id: str | None = None,
        client_upload_id: str | None = None,
        idempotency_key: str | None = None,
        commit: bool = True,
    ) -> ElfisDocumentIntakeItem:
        # Idempotence réseau
        if idempotency_key:
            existing_idemp = self._repo.find_by_idempotency_key(
                organization_id=organization_id, idempotency_key=idempotency_key
            )
            if existing_idemp:
                return existing_idemp

        upload_session: ElfisDocumentUploadSession | None = None
        if upload_session_id:
            upload_session = self._upload_sessions.get_session(
                upload_session_id, organization_id
            )
            self._upload_sessions.assert_accepts_upload(
                upload_session,
                organization_id=organization_id,
                migration_session_id=migration_session_id,
                incoming_bytes=len(content),
            )
            if not migration_session_id:
                migration_session_id = upload_session.migration_session_id

        self._assert_quotas(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            incoming_count=1,
            incoming_bytes=len(content),
        )
        if migration_session_id:
            from app.migration_center.models import ElfisMigrationSession

            sess = self._db.get(ElfisMigrationSession, migration_session_id)
            if not sess or sess.organization_id != organization_id:
                raise DocumentIntakeNotFoundError(
                    "migration_session_not_found",
                    "Session de migration introuvable",
                )

        validation = validate_content(
            filename=filename,
            content=content,
            declared_mime=declared_mime,
            relative_path=relative_path,
        )
        try:
            fingerprint = self._fingerprint.compute_from_bytes(
                content,
                detected_mime_type=validation.detected_mime,
                normalized_extension=validation.extension,
            )
        except ValueError as exc:
            if str(exc) == "zip_too_many_entries":
                raise DocumentIntakeValidationError(
                    "zip_too_many_entries",
                    "Archive ZIP avec trop d'entrées",
                ) from exc
            raise
        checksum = fingerprint["sha256"]
        scan = self._scanner.scan(
            filename=validation.normalized_filename,
            head=content[:4096],
            size_bytes=len(content),
        )

        is_duplicate = False
        duplicate_of_id = None
        duplicate_type = DuplicateType.NONE.value
        duplicate_confidence = None
        duplicate_reason = None
        quarantine_reason = None
        reject_reason = None

        existing = self._repo.find_by_checksum(
            organization_id=organization_id, checksum_sha256=checksum
        )
        if existing:
            is_duplicate = True
            duplicate_of_id = existing.id
            duplicate_type = DuplicateType.EXACT.value
            duplicate_confidence = 1.0
            duplicate_reason = "exact_sha256"

        if validation.mime_mismatch or scan.verdict == "suspicious":
            quarantine_reason = (
                "mime_mismatch" if validation.mime_mismatch else "scanner_suspicious"
            )

        quarantined = quarantine_reason is not None
        put = self._storage.put(
            organization_id=organization_id,
            content=content,
            extension=validation.extension,
            namespace="quarantine" if quarantined else "temp",
        )

        mime = validation.detected_mime or validation.declared_mime
        now = datetime.utcnow()
        universal_id = allocate_universal_document_id(self._db)

        row = ElfisDocumentIntakeItem(
            id=str(uuid4()),
            intake_token=f"din_{uuid4().hex}",
            universal_document_id=universal_id,
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            upload_session_id=upload_session.id if upload_session else None,
            uploaded_by_user_id=actor_user_id,
            batch_id=batch_id,
            original_filename=validation.original_filename[:255],
            normalized_filename=validation.normalized_filename,
            relative_path=validation.relative_path,
            extension=validation.extension,
            format_id=validation.format_id,
            declared_mime=validation.declared_mime,
            detected_mime=validation.detected_mime,
            mime=mime,
            size_bytes=validation.size_bytes,
            checksum_sha256=checksum,
            status=DocumentLifecycleStatus.UPLOADED.value,
            lifecycle_status=DocumentLifecycleStatus.UPLOADED.value,
            origin=origin,
            storage_key=put.object_key,
            storage_provider=put.provider,
            storage_location=put.location,
            storage_bucket_or_root="document_intake",
            storage_object_key=put.object_key,
            storage_version=put.version,
            storage_metadata=dict(put.metadata or {}),
            fingerprint=fingerprint,
            fingerprint_version=int(fingerprint.get("schema_version") or 2),
            is_duplicate=is_duplicate,
            duplicate_of_id=duplicate_of_id,
            duplicate_type=duplicate_type,
            duplicate_of_item_id=duplicate_of_id,
            duplicate_confidence=duplicate_confidence,
            duplicate_reason=duplicate_reason,
            client_upload_id=client_upload_id,
            idempotency_key=idempotency_key,
            quarantine_reason=quarantine_reason,
            reject_reason=reject_reason,
            scan_verdict=scan.verdict,
            extract_later=validation.extract_later,
            preview_allowed=validation.preview_allowed,
            analysis_allowed=False,
            metadata_json={
                "schema_version": 1,
                "scan": scan.details,
                "format": validation.format_id,
            },
            last_activity_at=now,
            version=1,
            uploaded_at=now,
            validated_at=None,
        )
        self._repo.add(row, commit=False)

        publish_intake_event(
            self._db,
            event_type="document.fingerprint.created",
            item=row,
            actor_user_id=actor_user_id,
            metadata={"fingerprint_version": row.fingerprint_version},
            idempotency_key=f"document:fingerprint:{row.id}",
            commit=False,
        )

        # Lifecycle machine
        actor_kw = {
            "organization_id": organization_id,
            "actor_type": LifecycleActorType.USER.value
            if actor_user_id
            else LifecycleActorType.SYSTEM.value,
            "actor_user_id": actor_user_id,
            "commit": False,
        }
        self._lifecycle.mark_validating(row, reason_code="ingest_start", **actor_kw)

        if quarantine_reason:
            self._lifecycle.mark_quarantined(
                row, reason_code=quarantine_reason, **actor_kw
            )
        elif is_duplicate:
            self._lifecycle.mark_duplicate(
                row, reason_code="exact_sha256", **actor_kw
            )
        else:
            self._lifecycle.mark_validated(row, reason_code="content_ok", **actor_kw)
            if not validation.extract_later:
                self._lifecycle.mark_ready_for_analysis(
                    row, reason_code="prepared", **actor_kw
                )

        if commit:
            self._db.commit()
            self._db.refresh(row)

        logger.info(
            "document_intake_ingested",
            extra={
                "organization_id": organization_id,
                "document_intake_item_id": row.id,
                "universal_document_id": row.universal_document_id,
                "upload_session_id": row.upload_session_id,
                "migration_session_id": row.migration_session_id,
                "status": row.status,
                "storage_provider": row.storage_provider,
                "operation": "ingest",
                "result": "ok",
            },
        )

        publish_intake_event(
            self._db,
            event_type="document.uploaded",
            item=row,
            actor_user_id=actor_user_id,
            metadata={"format_id": row.format_id},
            idempotency_key=f"document:uploaded:{row.id}",
        )
        if row.status == IntakeItemStatus.DUPLICATE.value:
            publish_intake_event(
                self._db,
                event_type="document.duplicate_detected",
                item=row,
                actor_user_id=actor_user_id,
                metadata={"duplicate_of_id": duplicate_of_id},
                idempotency_key=f"document:duplicate:{row.id}",
            )
        elif row.status == IntakeItemStatus.QUARANTINED.value:
            publish_intake_event(
                self._db,
                event_type="document.rejected",
                item=row,
                actor_user_id=actor_user_id,
                metadata={"reason": quarantine_reason, "quarantined": True},
                idempotency_key=f"document:rejected:{row.id}",
            )
        elif row.status in (
            IntakeItemStatus.VALIDATED.value,
            IntakeItemStatus.READY_FOR_ANALYSIS.value,
        ):
            publish_intake_event(
                self._db,
                event_type="document.validated",
                item=row,
                actor_user_id=actor_user_id,
                idempotency_key=f"document:validated:{row.id}",
            )
            if row.status == IntakeItemStatus.READY_FOR_ANALYSIS.value:
                publish_intake_event(
                    self._db,
                    event_type="document.ready_for_analysis",
                    item=row,
                    actor_user_id=actor_user_id,
                    idempotency_key=f"document:ready:{row.id}",
                )

        if upload_session:
            self._analytics.recalculate(upload_session, publish=True)
            self._upload_sessions.touch_activity(upload_session)
            self._db.commit()
            try:
                if row.status == IntakeItemStatus.DUPLICATE.value:
                    self._activity.record_system_activity(
                        organization_id=organization_id,
                        migration_session_id=upload_session.migration_session_id,
                        activity_type="document_duplicate_detected",
                        title="Doublon exact détecté",
                        metadata={"upload_session_id": upload_session.id, "item_id": row.id},
                    )
                elif row.status == IntakeItemStatus.QUARANTINED.value:
                    self._activity.record_system_activity(
                        organization_id=organization_id,
                        migration_session_id=upload_session.migration_session_id,
                        activity_type="document_quarantined",
                        title="Fichier placé en quarantaine",
                        metadata={"upload_session_id": upload_session.id, "item_id": row.id},
                    )
            except Exception:
                logger.exception("intake_activity_failed")

        return row

    def ingest_batch(
        self,
        *,
        organization_id: int,
        files: list[dict[str, Any]],
        actor_user_id: int | None,
        migration_session_id: str | None = None,
        origin: str = IntakeOrigin.FOLDER.value,
        upload_session_id: str | None = None,
    ) -> tuple[str, list[ElfisDocumentIntakeItem], dict[str, int]]:
        """files: [{filename, content, declared_mime?, relative_path?, idempotency_key?}]"""
        if not files:
            raise DocumentIntakeValidationError("files_required", "Aucun fichier fourni")
        total_bytes = sum(len(f.get("content") or b"") for f in files)
        self._assert_quotas(
            organization_id=organization_id,
            migration_session_id=migration_session_id,
            incoming_count=len(files),
            incoming_bytes=total_bytes,
        )
        batch_id = str(uuid4())
        items: list[ElfisDocumentIntakeItem] = []
        stats = {"accepted": 0, "rejected": 0, "duplicates": 0, "quarantined": 0}
        for f in files:
            try:
                row = self.ingest_bytes(
                    organization_id=organization_id,
                    filename=str(f.get("filename") or "unnamed"),
                    content=f.get("content") or b"",
                    actor_user_id=actor_user_id,
                    declared_mime=f.get("declared_mime"),
                    migration_session_id=migration_session_id,
                    relative_path=f.get("relative_path"),
                    batch_id=batch_id,
                    origin=origin,
                    upload_session_id=upload_session_id,
                    client_upload_id=f.get("client_upload_id"),
                    idempotency_key=f.get("idempotency_key"),
                    commit=True,
                )
                items.append(row)
                if row.status == IntakeItemStatus.DUPLICATE.value:
                    stats["duplicates"] += 1
                    stats["accepted"] += 1
                elif row.status == IntakeItemStatus.QUARANTINED.value:
                    stats["quarantined"] += 1
                elif row.status == IntakeItemStatus.REJECTED.value:
                    stats["rejected"] += 1
                else:
                    stats["accepted"] += 1
            except DocumentIntakeValidationError:
                stats["rejected"] += 1
        if upload_session_id and migration_session_id:
            try:
                self._activity.record_system_activity(
                    organization_id=organization_id,
                    migration_session_id=migration_session_id,
                    activity_type="document_files_received",
                    title=f"{len(items)} fichiers reçus",
                    metadata={
                        "upload_session_id": upload_session_id,
                        "batch_id": batch_id,
                        "duplicates": stats["duplicates"],
                        "rejected": stats["rejected"],
                    },
                )
                self._db.commit()
            except Exception:
                logger.exception("batch_activity_failed")
        return batch_id, items, stats

    def cancel_item(
        self,
        item_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        reason: str | None = None,
    ) -> ElfisDocumentIntakeItem:
        row = self.get_for_org(item_id, organization_id)
        if row.status == IntakeItemStatus.CANCELLED.value:
            return row
        row.reject_reason = (reason or "cancelled_by_user")[:255]
        try:
            self._lifecycle.cancel(
                row,
                organization_id=organization_id,
                reason_code=row.reject_reason,
                actor_type=LifecycleActorType.USER.value,
                actor_user_id=actor_user_id,
                commit=True,
            )
        except Exception:
            # Fallback si transition impossible depuis l'état courant
            row.status = IntakeItemStatus.CANCELLED.value
            row.lifecycle_status = IntakeItemStatus.CANCELLED.value
            self._repo.save(row, commit=True)
        publish_intake_event(
            self._db,
            event_type="document.rejected",
            item=row,
            actor_user_id=actor_user_id,
            metadata={"reason": row.reject_reason, "cancelled": True},
            idempotency_key=f"document:cancelled:{row.id}",
        )
        if row.upload_session_id:
            try:
                sess = self._upload_sessions.get_session(
                    row.upload_session_id, organization_id
                )
                self._analytics.recalculate(sess)
                self._db.commit()
            except Exception:
                logger.exception("cancel_analytics_failed")
        return row
