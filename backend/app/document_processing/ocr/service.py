"""OCRService — orchestration métier (providers n'écrivent pas en DB)."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.ocr import metrics as ocr_metrics
from app.document_processing.ocr.exceptions import (
    OCRAccessDeniedError,
    OCRNotFoundError,
    OCRPermanentError,
    OCRRetryableError,
    OCRValidationError,
)
from app.document_processing.ocr.models import ElfisDocumentOCRPage, ElfisDocumentOCRResult
from app.document_processing.ocr.pipeline import (
    build_artifact_payload,
    materialize_temp_file,
    read_artifact_bytes,
    store_ocr_artifact,
)
from app.document_processing.ocr.policies import OCRAccessPolicy, OCRLimits
from app.document_processing.ocr.provider import OCRRequest
from app.document_processing.ocr.provider_registry import get_ocr_provider_registry
from app.document_processing.ocr.repository import OCRRepository
from app.document_processing.ocr.sanitization import round_confidence, sanitize_ocr_error, sanitize_warnings
from app.document_processing.ocr.selection import OCRProviderSelectionService
from app.document_processing.ocr.types import OCRPageStatus, OCRResultStatus, PIPELINE_OCR_V1
from app.document_processing.service import DocumentProcessingService
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject
from app.storage.storage_types import DocumentStatus

logger = logging.getLogger(__name__)


class DocumentOCRService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = OCRRepository(db)
        self._audit = audit_logger
        self._limits = OCRLimits.from_settings()
        self._access = OCRAccessPolicy()
        self._registry = get_ocr_provider_registry()
        self._selection = OCRProviderSelectionService(self._registry)

    def get_for_org(self, ocr_result_id: str, organization_id: int) -> ElfisDocumentOCRResult:
        row = self._repo.get(ocr_result_id)
        if not row or row.organization_id != organization_id:
            raise OCRAccessDeniedError("ocr_access_denied", "Introuvable")
        return row

    def get_platform(self, ocr_result_id: str) -> ElfisDocumentOCRResult:
        row = self._repo.get(ocr_result_id)
        if not row:
            raise OCRNotFoundError()
        return row

    def list_results(self, **kwargs):
        return self._repo.list_results(**kwargs)

    def list_pages(self, ocr_result_id: str):
        return self._repo.list_pages(ocr_result_id)

    def list_providers_public(self):
        return self._registry.list_public()

    def select_provider(self, *, mime_type: str, **kwargs):
        return self._selection.select(mime_type=mime_type, **kwargs)

    def prepare_temp(
        self,
        *,
        storage_object: ElfisStorageObject,
    ) -> Path:
        from app.storage.storage_registry import build_storage_provider

        provider = build_storage_provider(storage_object.provider)

        def _open():
            return provider.open_stream(
                namespace=storage_object.namespace, object_key=storage_object.object_key
            )

        return materialize_temp_file(
            size_bytes=int(storage_object.size_bytes or 0),
            open_stream=_open,
            limits=self._limits,
        )

    async def run_provider(
        self,
        *,
        document: ElfisDocumentRecord,
        version: ElfisDocumentVersion,
        storage_object: ElfisStorageObject,
        provider_key: str,
        temp_path: Path,
        correlation_id: str | None = None,
        noop_mode: str | None = None,
    ):
        provider = self._registry.get(provider_key)
        langs = [
            x.strip()
            for x in str(getattr(settings, "document_ocr_default_languages", "fra,eng") or "").split(",")
            if x.strip()
        ]
        req = OCRRequest(
            document_id=document.id,
            document_version_id=version.id,
            mime_type=storage_object.mime_type_detected
            or storage_object.mime_type_declared
            or version.mime_type
            or "application/octet-stream",
            language_hints=langs,
            temp_path=temp_path,
            options={
                **({} if not isinstance(getattr(settings, "_ocr_job_options", None), dict) else {}),
                **({"noop_mode": noop_mode} if noop_mode else {}),
            },
            correlation_id=correlation_id,
            max_pages=self._limits.max_pages,
            max_page_characters=self._limits.max_page_characters,
            max_text_characters=self._limits.max_text_characters,
            noop_mode=noop_mode,
        )
        return await provider.recognize(req)

    def persist_provider_result(
        self,
        *,
        document: ElfisDocumentRecord,
        version: ElfisDocumentVersion,
        job_id: str | None,
        provider_key: str,
        provider_version: str,
        selection_reason: str | None,
        result,
        force: bool = False,
    ) -> ElfisDocumentOCRResult:
        if not force:
            existing = self._repo.find_active(
                document_version_id=version.id,
                provider_key=provider_key,
                provider_version=provider_version,
            )
            if existing and existing.status in (
                OCRResultStatus.COMPLETED.value,
                OCRResultStatus.PARTIALLY_COMPLETED.value,
            ):
                return existing

        self._repo.supersede_active(
            document_version_id=version.id,
            provider_key=provider_key,
        )

        now = datetime.utcnow()
        status = OCRResultStatus.FAILED.value
        if result.success:
            status = (
                OCRResultStatus.PARTIALLY_COMPLETED.value
                if result.partially_completed
                else OCRResultStatus.COMPLETED.value
            )

        confs = [p.confidence for p in result.pages if p.confidence is not None]
        avg = round_confidence(sum(confs) / len(confs)) if confs else None
        text_len = sum(len(p.text or "") for p in result.pages)
        requires = bool(
            (avg is not None and avg < 0.55)
            or "low_confidence" in (result.warnings or [])
            or status == OCRResultStatus.PARTIALLY_COMPLETED.value
        )

        row = ElfisDocumentOCRResult(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            organization_id=document.organization_id,
            processing_job_id=job_id,
            provider_key=provider_key,
            provider_version=provider_version,
            status=OCRResultStatus.PROCESSING.value if result.success else status,
            extraction_method=result.extraction_method,
            page_count=len(result.pages),
            processed_page_count=len(result.pages),
            detected_languages_json=list(result.detected_languages or []),
            average_confidence=avg,
            text_length=text_len,
            requires_review=requires,
            warnings_json=sanitize_warnings(result.warnings),
            error_code=result.error_code,
            error_message_sanitized=sanitize_ocr_error(result.error_message_sanitized),
            selection_reason_code=selection_reason,
            started_at=now,
        )
        self._repo.add_result(row, commit=False)

        if not result.success:
            row.status = status
            row.completed_at = now
            self._db.commit()
            self._safe_audit(
                "record_document_ocr_failed",
                ocr_result_id=row.id,
                document_id=document.id,
                version_id=version.id,
                organization_id=document.organization_id,
                job_id=job_id,
                provider_key=provider_key,
                error_code=result.error_code,
            )
            return row

        # artefact
        raw, checksum, size = build_artifact_payload(
            document_version_id=version.id,
            provider_key=provider_key,
            provider_version=provider_version,
            extraction_method=result.extraction_method,
            result=result,
        )
        try:
            artifact = store_ocr_artifact(
                self._db,
                organization_id=document.organization_id,
                ocr_result_id=row.id,
                content=raw,
                checksum=checksum,
                limits=self._limits,
            )
        except ValueError as exc:
            row.status = OCRResultStatus.FAILED.value
            row.error_code = "artifact_failed"
            row.error_message_sanitized = sanitize_ocr_error(str(exc))
            row.completed_at = now
            self._db.commit()
            raise OCRPermanentError("artifact_failed", "Artefact OCR trop volumineux") from exc

        row.text_artifact_storage_object_id = artifact.id
        row.text_checksum_sha256 = checksum
        row.text_length = text_len
        row.status = status
        row.completed_at = now

        for p in result.pages:
            page_text = p.text or ""
            page_cs = hashlib.sha256(page_text.encode("utf-8")).hexdigest()
            self._repo.add_page(
                ElfisDocumentOCRPage(
                    id=str(uuid4()),
                    ocr_result_id=row.id,
                    page_number=p.page_number,
                    status=OCRPageStatus.EMPTY.value
                    if not page_text.strip()
                    else OCRPageStatus.COMPLETED.value,
                    character_count=len(page_text),
                    word_count=len(page_text.split()) if page_text else 0,
                    confidence=round_confidence(p.confidence),
                    detected_language=p.detected_language,
                    rotation_degrees=p.rotation_degrees,
                    text_checksum_sha256=page_cs,
                    warnings_json=sanitize_warnings(p.warnings),
                ),
                commit=False,
            )

        self._db.commit()
        self._db.refresh(row)
        ocr_metrics.incr("ocr_artifacts_created")
        ocr_metrics.incr("ocr_completed")
        self._safe_audit(
            "record_document_ocr_completed"
            if status == OCRResultStatus.COMPLETED.value
            else "record_document_ocr_partially_completed",
            ocr_result_id=row.id,
            document_id=document.id,
            version_id=version.id,
            organization_id=document.organization_id,
            job_id=job_id,
            provider_key=provider_key,
            provider_version=provider_version,
            extraction_method=result.extraction_method,
            page_count=row.page_count,
            text_length=row.text_length,
            score=avg,
            duration_ms=result.processing_duration_ms,
            requires_review=requires,
        )
        self._safe_audit(
            "record_document_ocr_artifact_created",
            ocr_result_id=row.id,
            document_id=document.id,
            version_id=version.id,
            organization_id=document.organization_id,
            text_length=row.text_length,
        )
        return row

    def open_text(
        self,
        ocr_result_id: str,
        organization_id: int,
        *,
        platform: bool = False,
        actor_user_id: int | None = None,
    ) -> tuple[bytes, ElfisDocumentOCRResult]:
        row = self.get_platform(ocr_result_id) if platform else self.get_for_org(ocr_result_id, organization_id)
        doc = self._db.get(ElfisDocumentRecord, row.document_id)
        if not doc or doc.organization_id != row.organization_id:
            raise OCRAccessDeniedError("document_missing", "Document introuvable")
        if doc.status in (DocumentStatus.DELETED.value, DocumentStatus.PURGED.value):
            raise OCRAccessDeniedError("document_unavailable", "Document inaccessible")
        if not row.text_artifact_storage_object_id:
            raise OCRNotFoundError("artifact_missing", "Artefact absent")
        obj = self._db.get(ElfisStorageObject, row.text_artifact_storage_object_id)
        if not obj:
            raise OCRNotFoundError("artifact_missing", "Artefact absent")
        data = read_artifact_bytes(obj)
        ocr_metrics.incr("ocr_text_accessed")
        self._safe_audit(
            "record_document_ocr_text_accessed",
            ocr_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            text_length=row.text_length,
            actor_user_id=actor_user_id,
        )
        return data, row

    def reject(
        self,
        ocr_result_id: str,
        organization_id: int,
        *,
        platform: bool = False,
    ) -> ElfisDocumentOCRResult:
        row = self.get_platform(ocr_result_id) if platform else self.get_for_org(ocr_result_id, organization_id)
        if row.status == OCRResultStatus.REJECTED.value:
            return row
        row.status = OCRResultStatus.REJECTED.value
        row.updated_at = datetime.utcnow()
        self._db.commit()
        self._safe_audit(
            "record_document_ocr_rejected",
            ocr_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
        )
        return row

    def request_retry(
        self,
        ocr_result_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
        force: bool = True,
    ):
        row = self.get_platform(ocr_result_id) if platform else self.get_for_org(ocr_result_id, organization_id)
        self._safe_audit(
            "record_document_ocr_retry_requested",
            ocr_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
        )
        pipe = getattr(settings, "document_ocr_default_pipeline", None) or PIPELINE_OCR_V1
        return DocumentProcessingService(self._db, audit_logger=self._audit).create_job(
            organization_id=row.organization_id,
            document_id=row.document_id,
            document_version_id=row.document_version_id,
            pipeline_key=pipe,
            metadata={"force_ocr": force, "from_ocr_result_id": row.id},
            requested_by_user_id=actor_user_id,
        )

    def assert_can_ocr(self, document: ElfisDocumentRecord, storage_object: ElfisStorageObject | None) -> None:
        if storage_object and storage_object.status == "quarantined":
            raise OCRValidationError("object_quarantined", "Document en quarantaine")
        if document.status == DocumentStatus.PURGED.value:
            raise OCRValidationError("document_purged", "Document purgé")

    def purge_artifacts_for_document(
        self,
        document_id: str,
        *,
        organization_id: int,
        legal_hold_active: bool = False,
    ) -> int:
        """
        Supprime les artefacts texte OCR d'un document (appelé lors de la purge physique).
        Legal hold → refus (0, exception).
        Tombstone ne conserve jamais le texte.
        """
        if legal_hold_active:
            raise OCRValidationError("legal_hold", "Legal hold bloque la purge OCR")
        from app.document_processing.ocr.pipeline import delete_artifact_bytes

        rows = self._repo.list_for_document(document_id)
        deleted = 0
        for row in rows:
            if row.organization_id != organization_id:
                continue
            oid = row.text_artifact_storage_object_id
            if oid:
                obj = self._db.get(ElfisStorageObject, oid)
                if obj:
                    try:
                        delete_artifact_bytes(obj)
                    except Exception:
                        pass
                    obj.status = "purged"
                row.text_artifact_storage_object_id = None
                deleted += 1
                self._safe_audit(
                    "record_document_ocr_artifact_deleted",
                    ocr_result_id=row.id,
                    document_id=document_id,
                    version_id=row.document_version_id,
                    organization_id=organization_id,
                )
            row.status = OCRResultStatus.SUPERSEDED.value
            row.updated_at = datetime.utcnow()
        self._db.flush()
        return deleted

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**{k: v for k, v in kwargs.items() if v is not None})
        except Exception:
            logger.debug("ocr_audit_failed", extra={"method": method}, exc_info=True)
