"""Service central Document Intelligence."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.document_intelligence.document_exceptions import (
    DocumentDisabledError,
    DocumentNotFoundError,
    DocumentOCRUnavailableError,
    DocumentValidationError,
)
from app.document_intelligence.document_logging import (
    safe_document_log_context,
    sanitize_document_error,
)
from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.document_intelligence.document_quality import text_sha256
from app.document_intelligence.document_registry import (
    DocumentExtractorRegistry,
    bootstrap_extractors,
    default_extractor_registry,
)
from app.document_intelligence.document_repository import DocumentExtractionRepository
from app.document_intelligence.document_schemas import (
    DocumentExtractionRequest,
    DocumentExtractionResult,
    DocumentExtractionView,
)
from app.document_intelligence.document_security import (
    assert_extension_matches_mime,
    assert_file_size,
    assert_mime_allowed,
    assert_safe_storage_path,
    assert_text_size,
    create_temp_file,
    safe_unlink,
)
from app.document_intelligence.document_types import ExtractionStatus
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_vault import VaultDocument
from app.schemas_vault import VaultArchiveStatus
from app.services.vault.storage_service import VaultStorageService

logger = logging.getLogger(__name__)


def _as_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _suffix_for_mime(mime: str) -> str:
    return {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }.get(mime, ".bin")


class DocumentIntelligenceService:
    def __init__(
        self,
        db: Session,
        *,
        registry: DocumentExtractorRegistry | None = None,
        storage: VaultStorageService | None = None,
        download_fn: Callable[[str], bytes] | None = None,
    ):
        self._db = db
        self._repo = DocumentExtractionRepository(db)
        self._registry = registry or bootstrap_extractors(default_extractor_registry)
        self._storage = storage or VaultStorageService()
        self._download_fn = download_fn

    def get_extraction(self, extraction_id: str) -> ElfisDocumentTextExtraction:
        row = self._repo.find_by_extraction_id(extraction_id)
        if not row:
            raise DocumentNotFoundError("Extraction introuvable")
        return row

    def get_or_create_pending(
        self,
        *,
        organization_id: int,
        vault_document_id: str,
        document_version: int,
        user_id: int | None = None,
    ) -> ElfisDocumentTextExtraction:
        existing = self._repo.find_for_document(
            organization_id=organization_id,
            vault_document_id=vault_document_id,
            document_version=document_version,
        )
        if existing:
            return existing
        now = datetime.utcnow()
        row = ElfisDocumentTextExtraction(
            id=str(uuid.uuid4()),
            extraction_id=str(uuid.uuid4()),
            organization_id=organization_id,
            user_id=user_id,
            vault_document_id=vault_document_id,
            document_version=document_version,
            extractor_name="pending",
            status=ExtractionStatus.PENDING,
            metadata_json={},
            warnings=[],
            errors=[],
            created_at=now,
            updated_at=now,
        )
        return self._repo.save(row)

    def to_view(self, row: ElfisDocumentTextExtraction) -> DocumentExtractionView:
        return DocumentExtractionView(
            extraction_id=row.extraction_id,
            status=row.status,
            extractor_name=row.extractor_name,
            page_count=row.page_count,
            text_length=row.text_length or 0,
            quality_score=float(row.quality_score) if row.quality_score is not None else None,
            confidence=float(row.confidence) if row.confidence is not None else None,
            requires_ocr=bool(row.requires_ocr),
            requires_review=bool(row.requires_review),
            language=row.language,
            warnings=list(row.warnings or []),
            created_at=row.created_at,
            completed_at=row.completed_at,
        )

    def text_preview(self, row: ElfisDocumentTextExtraction, *, max_chars: int = 2000) -> str:
        return (row.text_content or "")[:max_chars]

    def extract_document_text(
        self, request: DocumentExtractionRequest
    ) -> DocumentExtractionResult:
        if not settings.elfis_document_intelligence_enabled:
            raise DocumentDisabledError()

        doc = (
            self._db.query(VaultDocument)
            .filter(VaultDocument.id == request.vault_document_id)
            .first()
        )
        if not doc or doc.organization_id != request.organization_id:
            raise DocumentNotFoundError()
        if doc.archive_status == VaultArchiveStatus.deleted.value:
            raise DocumentNotFoundError("Document supprimé")

        version = int(request.document_version or doc.version or 1)
        idem = (request.idempotency_key or "").strip() or (
            f"document-text:{request.organization_id}:{request.vault_document_id}:{version}"
        )

        existing = self._repo.find_by_idempotency(idem) or self._repo.find_for_document(
            organization_id=request.organization_id,
            vault_document_id=request.vault_document_id,
            document_version=version,
        )
        if existing and existing.status in (
            ExtractionStatus.COMPLETED,
            ExtractionStatus.REQUIRES_OCR,
            ExtractionStatus.REQUIRES_REVIEW,
            ExtractionStatus.PROCESSING,
        ):
            return self._to_result(existing, created=False, idempotent_reuse=True)

        mime = assert_mime_allowed(doc.mime_type or "application/pdf")
        assert_extension_matches_mime(doc.original_filename, mime)
        if doc.file_size:
            assert_file_size(int(doc.file_size))

        now = datetime.utcnow()
        row = existing or ElfisDocumentTextExtraction(
            id=str(uuid.uuid4()),
            extraction_id=str(uuid.uuid4()),
            organization_id=request.organization_id,
            user_id=request.user_id,
            vault_document_id=request.vault_document_id,
            document_version=version,
            extractor_name="pending",
            status=ExtractionStatus.PENDING,
            mime_type=mime,
            filename=doc.original_filename,
            file_size_bytes=doc.file_size,
            metadata_json={},
            warnings=[],
            errors=[],
            idempotency_key=idem,
            correlation_id=request.correlation_id or str(uuid.uuid4()),
            job_id=request.job_id,
            source_event_id=request.source_event_id,
            created_at=now,
            updated_at=now,
        )
        row.status = ExtractionStatus.PENDING
        row.mime_type = mime
        row.filename = doc.original_filename
        row.file_size_bytes = doc.file_size
        row.idempotency_key = idem
        row.job_id = request.job_id or row.job_id
        row.correlation_id = request.correlation_id or row.correlation_id
        self._repo.save(row)
        self._publish(EventNames.DOCUMENT_EXTRACTION_CREATED, row)

        row.status = ExtractionStatus.PROCESSING
        row.started_at = datetime.utcnow()
        self._repo.save(row)
        self._publish(EventNames.DOCUMENT_EXTRACTION_STARTED, row)

        temp_path: Path | None = None
        started = time.monotonic()
        try:
            content = request.content_bytes
            if content is None:
                storage_path = assert_safe_storage_path(doc.storage_path)
                if self._download_fn is not None:
                    content = self._download_fn(storage_path)
                else:
                    content = self._storage.download_bytes(storage_path=storage_path)
            assert_file_size(len(content))

            extractor = self._registry.for_mime(mime)
            if extractor is None:
                raise DocumentValidationError(f"Aucun extracteur pour {mime}")

            temp_path = create_temp_file(suffix=_suffix_for_mime(mime), content=content)
            output = extractor.extract(
                path=temp_path, mime_type=mime, filename=doc.original_filename or "document"
            )

            try:
                assert_text_size(output.text)
            except DocumentValidationError as exc:
                row.status = ExtractionStatus.REQUIRES_REVIEW
                row.requires_review = True
                row.requires_ocr = bool(output.requires_ocr)
                row.text_content = None
                row.text_length = len(output.text.encode("utf-8"))
                row.last_error = sanitize_document_error(exc.message)
                row.warnings = list(output.warnings) + ["text_too_large"]
                row.errors = [exc.message]
                row.extractor_name = extractor.extractor_name
                row.extractor_version = extractor.extractor_version
                row.page_count = output.page_count
                row.quality_score = output.quality_score
                row.confidence = output.confidence
                row.completed_at = datetime.utcnow()
                self._repo.save(row)
                self._publish(EventNames.DOCUMENT_EXTRACTION_REQUIRES_REVIEW, row)
                return self._to_result(row, created=True)

            row.extractor_name = extractor.extractor_name
            row.extractor_version = extractor.extractor_version
            row.provider = None
            row.page_count = output.page_count
            row.text_content = output.text
            row.text_hash = text_sha256(output.text)
            row.text_length = len(output.text)
            row.quality_score = output.quality_score
            row.confidence = output.confidence
            row.requires_ocr = bool(output.requires_ocr)
            row.requires_review = bool(output.requires_review)
            row.language = output.language
            row.metadata_json = dict(output.metadata or {})
            row.warnings = list(output.warnings or [])
            row.errors = []
            row.last_error = None
            row.completed_at = datetime.utcnow()

            if output.requires_ocr and not output.text:
                row.status = ExtractionStatus.REQUIRES_OCR
                row.text_content = ""
                self._repo.save(row)
                self._publish(EventNames.DOCUMENT_EXTRACTION_REQUIRES_OCR, row)
            elif output.requires_ocr:
                row.status = ExtractionStatus.REQUIRES_OCR
                self._repo.save(row)
                self._publish(EventNames.DOCUMENT_EXTRACTION_REQUIRES_OCR, row)
            elif output.requires_review:
                row.status = ExtractionStatus.REQUIRES_REVIEW
                self._repo.save(row)
                self._publish(EventNames.DOCUMENT_EXTRACTION_REQUIRES_REVIEW, row)
            else:
                row.status = ExtractionStatus.COMPLETED
                self._repo.save(row)
                self._publish(EventNames.DOCUMENT_EXTRACTION_COMPLETED, row)

            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "document_extraction_done",
                extra=safe_document_log_context(
                    extraction_id=row.extraction_id,
                    vault_document_id=row.vault_document_id,
                    organization_id=row.organization_id,
                    extractor_name=row.extractor_name,
                    status=row.status,
                    file_size_bytes=row.file_size_bytes,
                    page_count=row.page_count,
                    text_length=row.text_length,
                    quality_score=float(row.quality_score) if row.quality_score is not None else None,
                    confidence=float(row.confidence) if row.confidence is not None else None,
                    requires_ocr=row.requires_ocr,
                    duration_ms=duration_ms,
                    job_id=row.job_id,
                    correlation_id=row.correlation_id,
                ),
            )
            return self._to_result(row, created=True)

        except DocumentOCRUnavailableError as exc:
            return self._fail_or_block(row, exc.message, status=ExtractionStatus.BLOCKED)
        except DocumentValidationError as exc:
            return self._fail_or_block(row, exc.message, status=ExtractionStatus.FAILED)
        except Exception as exc:
            msg = sanitize_document_error(str(exc)) or "erreur extraction"
            return self._fail_or_block(row, msg, status=ExtractionStatus.FAILED)
        finally:
            safe_unlink(temp_path)

    def _fail_or_block(
        self, row: ElfisDocumentTextExtraction, message: str, *, status: str
    ) -> DocumentExtractionResult:
        row.status = status
        row.failed_at = datetime.utcnow() if status == ExtractionStatus.FAILED else None
        row.completed_at = datetime.utcnow()
        row.last_error = sanitize_document_error(message)
        row.errors = [row.last_error] if row.last_error else []
        if status == ExtractionStatus.BLOCKED:
            row.requires_ocr = True
            row.requires_review = True
        self._repo.save(row)
        event = (
            EventNames.DOCUMENT_EXTRACTION_REQUIRES_OCR
            if status in (ExtractionStatus.REQUIRES_OCR, ExtractionStatus.BLOCKED)
            else EventNames.DOCUMENT_EXTRACTION_FAILED
        )
        self._publish(event, row)
        logger.error(
            "document_extraction_error",
            extra=safe_document_log_context(
                extraction_id=row.extraction_id,
                vault_document_id=row.vault_document_id,
                organization_id=row.organization_id,
                status=row.status,
            ),
        )
        return self._to_result(row, created=True)

    def _publish(self, event_name: str, row: ElfisDocumentTextExtraction) -> None:
        safe_publish(
            self._db,
            DomainEvent(
                event_name=event_name,
                organization_id=row.organization_id,
                aggregate_type="document_text_extraction",
                aggregate_id=row.extraction_id,
                payload={
                    "extraction_id": row.extraction_id,
                    "vault_document_id": row.vault_document_id,
                    "organization_id": row.organization_id,
                    "status": row.status,
                    "extractor_name": row.extractor_name,
                    "text_length": row.text_length or 0,
                    "quality_score": float(row.quality_score)
                    if row.quality_score is not None
                    else None,
                    "confidence": float(row.confidence) if row.confidence is not None else None,
                    "requires_ocr": bool(row.requires_ocr),
                    "requires_review": bool(row.requires_review),
                    "job_id": row.job_id,
                    "correlation_id": row.correlation_id,
                },
                metadata={"source": "document_intelligence"},
                correlation_id=_as_uuid(row.correlation_id) or uuid.uuid4(),
                causation_id=_as_uuid(row.source_event_id),
            ),
        )

    def _to_result(
        self,
        row: ElfisDocumentTextExtraction,
        *,
        created: bool,
        idempotent_reuse: bool = False,
    ) -> DocumentExtractionResult:
        return DocumentExtractionResult(
            extraction_id=row.extraction_id,
            vault_document_id=row.vault_document_id,
            status=row.status,
            extractor_name=row.extractor_name,
            text_length=row.text_length or 0,
            quality_score=float(row.quality_score) if row.quality_score is not None else None,
            confidence=float(row.confidence) if row.confidence is not None else None,
            requires_ocr=bool(row.requires_ocr),
            requires_review=bool(row.requires_review),
            created=created,
            idempotent_reuse=idempotent_reuse,
            job_id=row.job_id,
        )
