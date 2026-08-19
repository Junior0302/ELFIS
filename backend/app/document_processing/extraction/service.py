"""DocumentExtractionService — orchestration métier."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.extraction import metrics as extr_metrics
from app.document_processing.extraction.exceptions import (
    ExtractionAccessDeniedError,
    ExtractionNotFoundError,
    ExtractionPermanentError,
    ExtractionRetryableError,
    ExtractionValidationError,
)
from app.document_processing.extraction.models import (
    ElfisDocumentExtractedField,
    ElfisDocumentExtractionResult,
    ElfisDocumentExtractionReview,
)
from app.document_processing.extraction.pipeline import (
    build_extraction_artifact_payload,
    delete_extraction_artifact_bytes,
    read_extraction_artifact_bytes,
    store_extraction_artifact,
)
from app.document_processing.extraction.policies import ExtractionAccessPolicy, ExtractionLimits
from app.document_processing.extraction.provider import (
    ExtractedFieldPayload,
    ExtractionProviderResult,
    ExtractionRequest,
)
from app.document_processing.extraction.provider_registry import get_extraction_provider_registry
from app.document_processing.extraction.repository import ExtractionRepository
from app.document_processing.extraction.sanitization import (
    mask_display_value,
    round_confidence,
    sanitize_validation_summary,
    sanitize_warnings,
)
from app.document_processing.extraction.schema_registry import get_extraction_schema_registry
from app.document_processing.extraction.selection import (
    ExtractionSchemaSelectionService,
    ExtractionSourceSelectionService,
)
from app.document_processing.extraction.types import ExtractionResultStatus, PIPELINE_EXTRACTION_V1
from app.document_processing.extraction.validation import ExtractionSchemaValidator, SchemaValidationResult
from app.document_processing.ocr.service import DocumentOCRService
from app.document_processing.service import DocumentProcessingService
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject
from app.storage.storage_types import DocumentStatus

logger = logging.getLogger(__name__)


def _decimal_json(v: Any) -> Any:
    if isinstance(v, Decimal):
        return str(v)
    return v


class DocumentExtractionService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = ExtractionRepository(db)
        self._audit = audit_logger
        self._limits = ExtractionLimits.from_settings()
        self._policy = ExtractionAccessPolicy()
        self._validator = ExtractionSchemaValidator()
        self._schema_sel = ExtractionSchemaSelectionService()
        self._schemas = get_extraction_schema_registry()

    def list_providers_public(self) -> list[dict]:
        return get_extraction_provider_registry().list_public()

    def list_schemas_public(self) -> list[dict]:
        return self._schemas.list_public()

    def select_schema(self, **kwargs) -> Any:
        return self._schema_sel.select(**kwargs)

    def select_source(
        self, *, organization_id: int, document_id: str, document_version_id: str
    ):
        return ExtractionSourceSelectionService(self._db).select(
            organization_id=organization_id,
            document_id=document_id,
            document_version_id=document_version_id,
        )

    def load_source_text(
        self,
        *,
        ocr_result_id: str,
        organization_id: int,
        document_version_id: str,
    ) -> tuple[str, dict[str, Any]]:
        """Charge le texte via OCRAccessPolicy (open_text) — jamais d'autre version."""
        ocr_svc = DocumentOCRService(self._db, audit_logger=self._audit)
        data, ocr_row = ocr_svc.open_text(ocr_result_id, organization_id, platform=False)
        if ocr_row.document_version_id != document_version_id:
            raise ExtractionValidationError("ocr_version_mismatch", "OCRResult d'une autre version")
        if len(data) > self._limits.max_source_characters * 4:
            raise ExtractionValidationError("source_too_large", "Artefact OCR trop volumineux")
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ExtractionValidationError("ocr_artifact_invalid", "Artefact OCR illisible") from exc
        pages = payload.get("pages") or []
        texts: list[str] = []
        page_meta: list[dict[str, Any]] = []
        for p in pages:
            if not isinstance(p, dict):
                continue
            t = str(p.get("text") or "")
            texts.append(t)
            page_meta.append(
                {
                    "page_number": p.get("page_number"),
                    "confidence": p.get("confidence"),
                    "char_count": len(t),
                }
            )
        text = "\n".join(texts)
        if len(text) > self._limits.max_source_characters:
            raise ExtractionValidationError("source_too_large", "Texte source trop long")
        # Persiste un marqueur source (pas le texte) — texte retourné au caller pour perform immédiat
        return text, {"ocr_result_id": ocr_result_id, "page_count": len(page_meta), "pages": page_meta}

    async def run_provider(
        self,
        *,
        provider_key: str,
        request: ExtractionRequest,
    ) -> ExtractionProviderResult:
        provider = get_extraction_provider_registry().get(provider_key)
        return await provider.extract(request)

    def validate_fields(
        self, schema_key: str, schema_version: str, fields: dict[str, ExtractedFieldPayload]
    ) -> SchemaValidationResult:
        schema = self._schemas.get(schema_key, schema_version)
        return self._validator.validate(
            schema,
            fields,
            max_fields=self._limits.max_fields,
            max_field_length=self._limits.max_field_length,
            review_threshold=self._limits.review_threshold,
        )

    def persist_result(
        self,
        *,
        document: ElfisDocumentRecord,
        version: ElfisDocumentVersion,
        job_id: str | None,
        ocr_result_id: str | None,
        classification_id: str | None,
        schema_key: str,
        schema_version: str,
        provider_key: str,
        provider_version: str,
        selection_reason: str | None,
        source_reason: str | None,
        effective_document_type: str | None,
        result: ExtractionProviderResult,
        validation: SchemaValidationResult,
        force: bool = False,
        idempotency_hash: str = "default",
    ) -> ElfisDocumentExtractionResult:
        if not force:
            existing = self._repo.find_active(
                document_version_id=version.id,
                ocr_result_id=ocr_result_id,
                schema_key=schema_key,
                schema_version=schema_version,
                provider_key=provider_key,
                provider_version=provider_version,
                idempotency_hash=idempotency_hash,
            )
            if existing and existing.status in (
                ExtractionResultStatus.COMPLETED.value,
                ExtractionResultStatus.CONFIRMED.value,
            ):
                return existing

        now = datetime.utcnow()
        row_id = str(uuid4())
        raw, checksum, _size = build_extraction_artifact_payload(
            document_version_id=version.id,
            ocr_result_id=ocr_result_id,
            schema_key=schema_key,
            schema_version=schema_version,
            provider_key=provider_key,
            provider_version=provider_version,
            result=result,
            validation=validation,
        )
        artifact = store_extraction_artifact(
            self._db,
            organization_id=document.organization_id,
            extraction_result_id=row_id,
            content=raw,
            checksum=checksum,
            limits=self._limits,
        )

        if force:
            self._repo.supersede_active(
                document_version_id=version.id,
                schema_key=schema_key,
                provider_key=provider_key,
                except_id=None,
            )

        if not result.success:
            status = ExtractionResultStatus.FAILED.value
        elif not validation.valid:
            status = ExtractionResultStatus.INVALID.value
        elif result.partially_completed or validation.missing_required_fields:
            status = ExtractionResultStatus.PARTIALLY_COMPLETED.value
        else:
            status = ExtractionResultStatus.COMPLETED.value

        requires = bool(validation.requires_review)
        if not getattr(settings, "document_extraction_auto_confirm", False):
            if status == ExtractionResultStatus.COMPLETED.value:
                requires = True  # revue humaine par défaut

        schema = self._schemas.get(schema_key, schema_version)
        fmap = schema.field_map()

        row = ElfisDocumentExtractionResult(
            id=row_id,
            organization_id=document.organization_id,
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=job_id,
            ocr_result_id=ocr_result_id,
            classification_id=classification_id,
            schema_key=schema_key,
            schema_version=schema_version,
            provider_key=provider_key,
            provider_version=provider_version,
            status=status,
            confidence_score=round_confidence(result.confidence_score),
            requires_review=requires,
            fields_count=len(validation.normalized_fields or result.fields),
            valid_fields_count=len(validation.normalized_fields)
            - len(validation.invalid_fields),
            invalid_fields_count=len(validation.invalid_fields),
            missing_required_fields_count=len(validation.missing_required_fields),
            result_artifact_storage_object_id=artifact.id,
            result_checksum_sha256=checksum,
            validation_summary_json=sanitize_validation_summary(validation.to_summary_dict()),
            warnings_json=sanitize_warnings(list(result.warnings or []) + list(validation.warnings or [])),
            error_code=result.error_code,
            error_message_sanitized=(result.error_message_sanitized or "")[:255] or None,
            selection_reason_code=selection_reason,
            source_reason_code=source_reason,
            effective_document_type=effective_document_type,
            idempotency_hash=idempotency_hash,
            started_at=now,
            completed_at=now,
        )
        self._repo.add_result(row, commit=False)

        fields_src = validation.normalized_fields or result.fields
        for path, payload in fields_src.items():
            fdef = fmap.get(path)
            sensitive = bool(fdef.sensitive) if fdef else True
            norm_json = None
            if not sensitive and payload.normalized_value is not None:
                norm_json = _decimal_json(payload.normalized_value)
                if isinstance(norm_json, str) and len(norm_json) > 200:
                    norm_json = None
            page = None
            if payload.evidence:
                page = payload.evidence[0].page
            self._repo.add_field(
                ElfisDocumentExtractedField(
                    id=str(uuid4()),
                    extraction_result_id=row.id,
                    field_path=path,
                    field_type=payload.field_type,
                    status=payload.status,
                    normalized_value_json=norm_json,
                    display_value_masked=mask_display_value(
                        path, payload.normalized_value or payload.value, sensitive=sensitive
                    ),
                    confidence_score=round_confidence(payload.confidence),
                    source_page=page,
                    evidence_reference_json=[
                        {k: v for k, v in {"page": e.page, "rule": e.rule, "evidence_code": e.evidence_code}.items() if v}
                        for e in (payload.evidence or [])[:3]
                    ],
                    validation_codes_json=list(payload.validation_codes or [])[:10],
                ),
                commit=False,
            )

        self._db.commit()
        self._db.refresh(row)
        extr_metrics.incr("extraction_artifacts_created")
        extr_metrics.incr("extraction_completed")
        audit_m = (
            "record_document_extraction_completed"
            if status == ExtractionResultStatus.COMPLETED.value
            else (
                "record_document_extraction_invalid"
                if status == ExtractionResultStatus.INVALID.value
                else "record_document_extraction_partially_completed"
            )
        )
        self._safe_audit(
            audit_m,
            extraction_result_id=row.id,
            document_id=document.id,
            version_id=version.id,
            ocr_result_id=ocr_result_id,
            organization_id=document.organization_id,
            job_id=job_id,
            schema_key=schema_key,
            schema_version=schema_version,
            provider_key=provider_key,
            provider_version=provider_version,
            status=status,
            fields_count=row.fields_count,
            missing_count=row.missing_required_fields_count,
            invalid_count=row.invalid_fields_count,
            requires_review=requires,
            score=row.confidence_score,
            duration_ms=result.processing_duration_ms,
        )
        self._safe_audit(
            "record_document_extraction_artifact_created",
            extraction_result_id=row.id,
            document_id=document.id,
            version_id=version.id,
            organization_id=document.organization_id,
            fields_count=row.fields_count,
        )
        return row

    def get_for_org(self, extraction_id: str, organization_id: int) -> ElfisDocumentExtractionResult:
        row = self._repo.get(extraction_id)
        if not row or row.organization_id != organization_id:
            raise ExtractionNotFoundError("not_found", "Extraction introuvable")
        return row

    def get_platform(self, extraction_id: str) -> ElfisDocumentExtractionResult:
        row = self._repo.get(extraction_id)
        if not row:
            raise ExtractionNotFoundError("not_found", "Extraction introuvable")
        return row

    def list_results(self, **kwargs):
        return self._repo.list_results(**kwargs)

    def list_fields(self, extraction_id: str):
        return self._repo.list_fields(extraction_id)

    def open_content(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        platform: bool = False,
        actor_user_id: int | None = None,
    ) -> tuple[bytes, ElfisDocumentExtractionResult]:
        row = self.get_platform(extraction_id) if platform else self.get_for_org(extraction_id, organization_id)
        doc = self._db.get(ElfisDocumentRecord, row.document_id)
        if not doc or doc.organization_id != row.organization_id:
            raise ExtractionAccessDeniedError("document_missing", "Document introuvable")
        self._policy.assert_document_readable(doc, for_content=True)
        if not row.result_artifact_storage_object_id:
            raise ExtractionNotFoundError("artifact_missing", "Artefact absent")
        obj = self._db.get(ElfisStorageObject, row.result_artifact_storage_object_id)
        if not obj:
            raise ExtractionNotFoundError("artifact_missing", "Artefact absent")
        data = read_extraction_artifact_bytes(obj)
        if len(data) > self._limits.max_result_bytes:
            raise ExtractionAccessDeniedError("artifact_too_large", "Artefact trop volumineux")
        extr_metrics.incr("extraction_content_accessed")
        self._safe_audit(
            "record_document_extraction_content_accessed",
            extraction_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            fields_count=row.fields_count,
            actor_user_id=actor_user_id,
        )
        return data, row

    def confirm(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentExtractionResult:
        row = self.get_platform(extraction_id) if platform else self.get_for_org(extraction_id, organization_id)
        if row.status == ExtractionResultStatus.CONFIRMED.value:
            return row
        if row.status == ExtractionResultStatus.REJECTED.value:
            raise ExtractionValidationError("already_rejected", "Résultat déjà rejeté")
        row.status = ExtractionResultStatus.CONFIRMED.value
        row.requires_review = False
        row.updated_at = datetime.utcnow()
        self._repo.add_review(
            ElfisDocumentExtractionReview(
                id=str(uuid4()),
                extraction_result_id=row.id,
                action="confirm",
                actor_user_id=actor_user_id,
            ),
            commit=False,
        )
        self._db.commit()
        self._db.refresh(row)
        self._safe_audit(
            "record_document_extraction_confirmed",
            extraction_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            schema_key=row.schema_key,
            status=row.status,
        )
        return row

    def reject(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        reason: str | None = None,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentExtractionResult:
        row = self.get_platform(extraction_id) if platform else self.get_for_org(extraction_id, organization_id)
        row.status = ExtractionResultStatus.REJECTED.value
        row.updated_at = datetime.utcnow()
        self._repo.add_review(
            ElfisDocumentExtractionReview(
                id=str(uuid4()),
                extraction_result_id=row.id,
                action="reject",
                actor_user_id=actor_user_id,
                reason=(reason or "")[:255] or None,
            ),
            commit=False,
        )
        self._db.commit()
        self._db.refresh(row)
        self._safe_audit(
            "record_document_extraction_rejected",
            extraction_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
        )
        return row

    def correct(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        patch: dict[str, Any],
        actor_user_id: int | None = None,
        reason: str | None = None,
        platform: bool = False,
    ) -> ElfisDocumentExtractionResult:
        """Patch de champs — conserve provider_value dans l'artefact ; ne détruit pas l'historique."""
        row = self.get_platform(extraction_id) if platform else self.get_for_org(extraction_id, organization_id)
        if row.status in (ExtractionResultStatus.REJECTED.value, ExtractionResultStatus.SUPERSEDED.value):
            raise ExtractionValidationError("not_correctable", "Résultat non corrigible")
        doc = self._db.get(ElfisDocumentRecord, row.document_id)
        if doc:
            self._policy.assert_document_readable(doc, for_content=False)
            if doc.status == DocumentStatus.DELETED.value:
                raise ExtractionValidationError("document_deleted", "Correction bloquée")

        data, _ = self.open_content(
            extraction_id, organization_id, platform=platform, actor_user_id=actor_user_id
        )
        payload = json.loads(data.decode("utf-8"))
        fields_raw = payload.get("fields") or {}
        schema = self._schemas.get(row.schema_key, row.schema_version)
        fmap = schema.field_map()

        corrections: dict[str, Any] = {}
        rebuilt: dict[str, ExtractedFieldPayload] = {}
        for path, fobj in fields_raw.items():
            if not isinstance(fobj, dict):
                continue
            rebuilt[path] = ExtractedFieldPayload(
                field_path=path,
                field_type=str(fobj.get("field_type") or "string"),
                value=fobj.get("value"),
                normalized_value=fobj.get("normalized_value"),
                confidence=fobj.get("confidence"),
                status=str(fobj.get("status") or "extracted"),
            )

        for path, new_val in (patch or {}).items():
            if path not in fmap:
                raise ExtractionValidationError("unknown_field", f"Champ inconnu: {path}")
            old = rebuilt.get(path)
            provider_val = old.value if old else None
            rebuilt[path] = ExtractedFieldPayload(
                field_path=path,
                field_type=fmap[path].field_type.value,
                value=new_val,
                normalized_value=new_val,
                confidence=1.0,
                status="corrected",
            )
            corrections[path] = {
                "provider_value": provider_val,
                "corrected_value": new_val,
                "corrected_by": actor_user_id,
                "corrected_at": datetime.utcnow().isoformat() + "Z",
            }

        validation = self._validator.validate(
            schema,
            rebuilt,
            max_fields=self._limits.max_fields,
            max_field_length=self._limits.max_field_length,
            review_threshold=self._limits.review_threshold,
        )
        if not validation.valid and validation.invalid_fields:
            raise ExtractionValidationError("schema_invalid_after_correction", "Correction invalide")

        provider_result = ExtractionProviderResult(
            success=True,
            provider_key=row.provider_key,
            provider_version=row.provider_version,
            fields=validation.normalized_fields,
            confidence_score=row.confidence_score,
        )
        raw, checksum, _ = build_extraction_artifact_payload(
            document_version_id=row.document_version_id,
            ocr_result_id=row.ocr_result_id,
            schema_key=row.schema_key,
            schema_version=row.schema_version,
            provider_key=row.provider_key,
            provider_version=row.provider_version,
            result=provider_result,
            validation=validation,
            corrections=corrections,
        )
        artifact = store_extraction_artifact(
            self._db,
            organization_id=row.organization_id,
            extraction_result_id=row.id,
            content=raw,
            checksum=checksum,
            limits=self._limits,
            purpose="extraction_artifact_corrected",
        )
        row.result_artifact_storage_object_id = artifact.id
        row.result_checksum_sha256 = checksum
        row.validation_summary_json = sanitize_validation_summary(validation.to_summary_dict())
        row.fields_count = len(validation.normalized_fields)
        row.invalid_fields_count = len(validation.invalid_fields)
        row.missing_required_fields_count = len(validation.missing_required_fields)
        row.requires_review = True
        row.updated_at = datetime.utcnow()

        # maj index fields
        existing_fields = {f.field_path: f for f in self._repo.list_fields(row.id)}
        for path, payload in validation.normalized_fields.items():
            fdef = fmap.get(path)
            sensitive = bool(fdef.sensitive) if fdef else True
            ef = existing_fields.get(path)
            if ef:
                ef.status = "corrected"
                ef.manually_corrected = True
                ef.display_value_masked = mask_display_value(
                    path, payload.normalized_value or payload.value, sensitive=sensitive
                )
                if not sensitive:
                    ef.normalized_value_json = _decimal_json(payload.normalized_value)
                ef.updated_at = datetime.utcnow()

        self._repo.add_review(
            ElfisDocumentExtractionReview(
                id=str(uuid4()),
                extraction_result_id=row.id,
                action="correct",
                actor_user_id=actor_user_id,
                reason=(reason or "")[:255] or None,
                patch_summary_json={
                    "fields": list(corrections.keys())[:50],
                    "count": len(corrections),
                },
            ),
            commit=False,
        )
        self._db.commit()
        self._db.refresh(row)
        self._safe_audit(
            "record_document_extraction_corrected",
            extraction_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            fields_count=len(corrections),
        )
        return row

    def request_reextract(
        self,
        extraction_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
        force: bool = True,
    ):
        row = self.get_platform(extraction_id) if platform else self.get_for_org(extraction_id, organization_id)
        self._safe_audit(
            "record_document_extraction_retry_requested",
            extraction_result_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
        )
        pipe = getattr(settings, "document_extraction_default_pipeline", None) or PIPELINE_EXTRACTION_V1
        return DocumentProcessingService(self._db, audit_logger=self._audit).create_job(
            organization_id=row.organization_id,
            document_id=row.document_id,
            document_version_id=row.document_version_id,
            pipeline_key=pipe,
            metadata={
                "force_extraction": force,
                "force_extraction_enabled": True,
                "from_extraction_result_id": row.id,
            },
            requested_by_user_id=actor_user_id,
        )

    def resolve_effective(self, *, organization_id: int, document_id: str, version_id: str | None = None):
        """EffectiveExtraction — représentation générique ELFIS, pas ComptaPilot."""
        items, _ = self._repo.list_results(
            organization_id=organization_id,
            document_id=document_id,
            version_id=version_id,
            limit=20,
        )
        for status in (
            ExtractionResultStatus.CONFIRMED.value,
            ExtractionResultStatus.COMPLETED.value,
            ExtractionResultStatus.PARTIALLY_COMPLETED.value,
            ExtractionResultStatus.INVALID.value,
        ):
            for row in items:
                if row.status == status:
                    return {
                        "extraction_result_id": row.id,
                        "status": row.status,
                        "schema_key": row.schema_key,
                        "schema_version": row.schema_version,
                        "requires_review": row.requires_review,
                        "document_version_id": row.document_version_id,
                        "fields_count": row.fields_count,
                        "missing_required_fields_count": row.missing_required_fields_count,
                    }
        return None

    def assert_can_extract(self, document: ElfisDocumentRecord, storage_object: ElfisStorageObject | None) -> None:
        quarantined = bool(storage_object and storage_object.status == "quarantined")
        self._policy.assert_can_extract(document, storage_quarantined=quarantined)

    def purge_artifacts_for_document(
        self,
        document_id: str,
        *,
        organization_id: int,
        legal_hold_active: bool = False,
    ) -> int:
        if legal_hold_active:
            raise ExtractionValidationError("legal_hold", "Legal hold bloque la purge extraction")
        rows = self._repo.list_for_document(document_id)
        deleted = 0
        for row in rows:
            if row.organization_id != organization_id:
                continue
            oid = row.result_artifact_storage_object_id
            if oid:
                obj = self._db.get(ElfisStorageObject, oid)
                if obj:
                    try:
                        delete_extraction_artifact_bytes(obj)
                    except Exception:
                        pass
                    obj.status = "purged"
                row.result_artifact_storage_object_id = None
                deleted += 1
                self._safe_audit(
                    "record_document_extraction_artifact_deleted",
                    extraction_result_id=row.id,
                    document_id=document_id,
                    version_id=row.document_version_id,
                    organization_id=organization_id,
                    schema_key=row.schema_key,
                    provider_key=row.provider_key,
                )
            row.status = ExtractionResultStatus.SUPERSEDED.value
            row.updated_at = datetime.utcnow()
        self._db.flush()
        return deleted

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**{k: v for k, v in kwargs.items() if v is not None})
        except Exception:
            logger.debug("extraction_audit_failed", exc_info=True)


def idempotency_hash_for(
    *,
    ocr_result_id: str | None,
    options: dict | None,
) -> str:
    raw = json.dumps(
        {"ocr": ocr_result_id or "", "opts": options or {}},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
