"""Étapes pipeline document_extraction_v1.

Transport inter-steps : artefacts StorageObject (draft), jamais cache process-local seul.
Le texte OCR n'apparaît jamais dans output_summary / metadata job.
"""

from __future__ import annotations

from app.config import settings
from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingPermanentError, ProcessingRetryableError
from app.document_processing.extraction.exceptions import (
    ExtractionPermanentError,
    ExtractionRetryableError,
    ExtractionValidationError,
)
from app.document_processing.extraction.pipeline import (
    read_json_artifact,
    store_provider_draft_artifact,
    store_text_draft_artifact,
)
from app.document_processing.extraction.policies import ExtractionLimits
from app.document_processing.extraction.provider import (
    ExtractedFieldPayload,
    ExtractionProviderResult,
    ExtractionRequest,
    FieldEvidence,
)
from app.document_processing.extraction.service import DocumentExtractionService, idempotency_hash_for
from app.document_processing.extraction.types import (
    STEP_FINALIZE_EXTRACTION,
    STEP_LOAD_EXTRACTION_SOURCE,
    STEP_PERFORM_EXTRACTION,
    STEP_PERSIST_EXTRACTION_ARTIFACT,
    STEP_RESOLVE_EFFECTIVE_TYPE,
    STEP_SELECT_EXTRACTION_SCHEMA,
    STEP_SELECT_EXTRACTION_SOURCE,
    STEP_VALIDATE_EXTRACTION,
)
from app.storage.storage_models import ElfisStorageObject


def _meta(ctx: ProcessingContext) -> dict:
    return dict(ctx.job.metadata_json or {})


def _set_meta(ctx: ProcessingContext, meta: dict) -> None:
    ctx.job.metadata_json = dict(meta)
    ctx.db.flush()


class ResolveEffectiveDocumentTypeStep:
    step_key = STEP_RESOLVE_EFFECTIVE_TYPE

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        pipeline = getattr(context.job, "pipeline_key", "") or ""
        is_bv = pipeline == "document_business_validation_v1" or meta.get(
            "force_business_validation_enabled"
        )
        if is_bv:
            if not getattr(settings, "document_business_validation_enabled", False):
                if not meta.get("force_business_validation_enabled"):
                    raise ProcessingPermanentError(
                        "business_validation_disabled", "Validation métier désactivée"
                    )
        elif not getattr(settings, "document_extraction_enabled", False):
            if not (meta.get("force_extraction_enabled") or meta.get("noop_mode")):
                raise ProcessingPermanentError("extraction_disabled", "Extraction désactivée")

        # type effectif : classification confirmée > document_type > unknown
        dtype = context.document.document_type or "unknown"
        classification_id = None
        confirmed = False
        requires_review = False
        try:
            from app.document_processing.classification.models import ElfisDocumentClassification
            from app.document_processing.classification.types import ClassificationStatus

            row = (
                context.db.query(ElfisDocumentClassification)
                .filter(
                    ElfisDocumentClassification.document_version_id == context.version.id,
                    ElfisDocumentClassification.organization_id == context.document.organization_id,
                )
                .order_by(ElfisDocumentClassification.created_at.desc())
                .first()
            )
            if row:
                classification_id = row.id
                requires_review = bool(row.requires_review)
                if row.confirmed_type:
                    dtype = row.confirmed_type
                    confirmed = True
                elif row.predicted_type:
                    dtype = row.predicted_type
                if row.status == getattr(ClassificationStatus, "CONFIRMED", None) and row.confirmed_type:
                    confirmed = True
                    dtype = row.confirmed_type
        except Exception:
            pass

        meta["_extraction_effective_type"] = {
            "type": dtype,
            "classification_id": classification_id,
            "confirmed": confirmed,
            "requires_review": requires_review,
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"effective_document_type": dtype, "confirmed": confirmed},
        )


class SelectExtractionSchemaStep:
    step_key = STEP_SELECT_EXTRACTION_SCHEMA

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        eff = meta.get("_extraction_effective_type") or {}
        svc = DocumentExtractionService(context.db)
        try:
            sel = svc.select_schema(
                effective_document_type=eff.get("type"),
                classification_id=eff.get("classification_id"),
                classification_confirmed=bool(eff.get("confirmed")),
                classification_requires_review=bool(eff.get("requires_review")),
            )
        except ExtractionValidationError as exc:
            raise ProcessingPermanentError(exc.code, exc.message) from exc
        meta["_extraction_schema"] = {
            "schema_key": sel.schema_key,
            "schema_version": sel.schema_version,
            "reason_code": sel.reason_code,
            "classification_id": sel.classification_id,
            "requires_review": sel.requires_review,
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "schema_key": sel.schema_key,
                "schema_version": sel.schema_version,
                "reason_code": sel.reason_code,
            },
        )


class SelectExtractionSourceStep:
    step_key = STEP_SELECT_EXTRACTION_SOURCE

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        svc = DocumentExtractionService(context.db)
        try:
            svc.assert_can_extract(context.document, context.storage_object)
            src = svc.select_source(
                organization_id=context.document.organization_id,
                document_id=context.document.id,
                document_version_id=context.version.id,
            )
        except ExtractionValidationError as exc:
            if exc.code == "object_quarantined":
                return ProcessingStepResult(
                    success=False,
                    status="blocked",
                    error_code=exc.code,
                    error_message_sanitized=exc.message,
                    retryable=False,
                )
            raise ProcessingPermanentError(exc.code, exc.message) from exc
        meta["_extraction_source"] = {
            "ocr_result_id": src.ocr_result_id,
            "reason_code": src.reason_code,
            "extraction_method": src.extraction_method,
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "ocr_result_id": src.ocr_result_id,
                "reason_code": src.reason_code,
            },
        )


class LoadExtractionSourceStep:
    step_key = STEP_LOAD_EXTRACTION_SOURCE

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        src = meta.get("_extraction_source") or {}
        ocr_id = src.get("ocr_result_id")
        if not ocr_id:
            raise ProcessingPermanentError("source_missing", "Source OCR absente")
        svc = DocumentExtractionService(context.db)
        try:
            text, info = svc.load_source_text(
                ocr_result_id=ocr_id,
                organization_id=context.document.organization_id,
                document_version_id=context.version.id,
            )
        except ExtractionValidationError as exc:
            raise ProcessingPermanentError(exc.code, exc.message) from exc

        limits = ExtractionLimits.from_settings()
        draft = store_text_draft_artifact(
            context.db,
            organization_id=context.document.organization_id,
            job_id=context.job.id,
            text=text,
            page_metadata=info.get("pages") or [],
            limits=limits,
        )
        meta["_extraction_source_artifact_id"] = draft.id
        meta["_extraction_source_page_count"] = info.get("page_count")
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "source_loaded": True,
                "page_count": info.get("page_count"),
                "char_count_bucket": min(len(text) // 1000, 500),
            },
        )


class PerformStructuredExtractionStep:
    step_key = STEP_PERFORM_EXTRACTION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        schema = meta.get("_extraction_schema") or {}
        src_art_id = meta.get("_extraction_source_artifact_id")
        if not src_art_id:
            raise ProcessingPermanentError("source_draft_missing", "Draft source absent")
        obj = context.db.get(ElfisStorageObject, src_art_id)
        if not obj:
            raise ProcessingPermanentError("source_draft_missing", "Draft source introuvable")
        draft = read_json_artifact(obj)
        text = str(draft.get("text") or "")
        pages = list(draft.get("pages") or [])

        provider_key = (
            meta.get("extraction_provider")
            or getattr(settings, "document_extraction_provider", None)
            or "noop"
        ).strip()
        svc = DocumentExtractionService(context.db)
        req = ExtractionRequest(
            document_id=context.document.id,
            document_version_id=context.version.id,
            organization_id=context.document.organization_id,
            schema_key=str(schema.get("schema_key") or "generic_document_v1"),
            schema_version=str(schema.get("schema_version") or "1"),
            effective_document_type=(meta.get("_extraction_effective_type") or {}).get("type"),
            source_text=text,
            page_metadata=pages,
            options={},
            correlation_id=context.job.correlation_id,
            max_text_characters=int(
                getattr(settings, "document_extraction_max_source_characters", 500_000) or 500_000
            ),
            noop_mode=meta.get("noop_mode"),
        )
        try:
            result = await svc.run_provider(provider_key=provider_key, request=req)
        except ExtractionRetryableError as exc:
            raise ProcessingRetryableError(exc.code, exc.message) from exc
        except ExtractionPermanentError as exc:
            raise ProcessingPermanentError(exc.code, exc.message) from exc

        # sérialise résultat provider dans draft artefact (sans laisser le texte source)
        provider_payload = {
            "schema": "extraction_provider_draft_v1",
            "success": result.success,
            "provider_key": result.provider_key,
            "provider_version": result.provider_version,
            "fields": {k: v.to_public_dict() for k, v in result.fields.items()},
            "warnings": list(result.warnings or [])[:20],
            "processing_duration_ms": result.processing_duration_ms,
            "retryable": result.retryable,
            "error_code": result.error_code,
            "error_message_sanitized": result.error_message_sanitized,
            "partially_completed": result.partially_completed,
            "confidence_score": result.confidence_score,
        }
        limits = ExtractionLimits.from_settings()
        draft_obj = store_provider_draft_artifact(
            context.db,
            organization_id=context.document.organization_id,
            job_id=context.job.id,
            provider_payload=provider_payload,
            limits=limits,
        )
        meta["_extraction_provider_draft_id"] = draft_obj.id
        meta["_extraction_provider_summary"] = {
            "provider_key": result.provider_key,
            "provider_version": result.provider_version,
            "fields_count": len(result.fields),
            "success": result.success,
            "partially_completed": result.partially_completed,
            "duration_ms": result.processing_duration_ms,
            "error_code": result.error_code,
        }
        _set_meta(context, meta)

        if not result.success:
            if result.retryable:
                raise ProcessingRetryableError(
                    result.error_code or "extraction_failed",
                    result.error_message_sanitized or "Extraction échouée",
                )
            raise ProcessingPermanentError(
                result.error_code or "extraction_failed",
                result.error_message_sanitized or "Extraction échouée",
            )
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "provider_key": result.provider_key,
                "fields_count": len(result.fields),
                "duration_ms": result.processing_duration_ms,
            },
        )


def _result_from_draft(payload: dict) -> ExtractionProviderResult:
    fields: dict[str, ExtractedFieldPayload] = {}
    for path, fobj in (payload.get("fields") or {}).items():
        if not isinstance(fobj, dict):
            continue
        evidences = []
        for e in fobj.get("evidence") or []:
            if isinstance(e, dict):
                evidences.append(
                    FieldEvidence(
                        page=e.get("page"),
                        rule=e.get("rule"),
                        evidence_code=e.get("evidence_code"),
                        method=e.get("method"),
                    )
                )
        fields[path] = ExtractedFieldPayload(
            field_path=path,
            field_type=str(fobj.get("field_type") or "string"),
            value=fobj.get("value"),
            normalized_value=fobj.get("normalized_value"),
            confidence=fobj.get("confidence"),
            status=str(fobj.get("status") or "extracted"),
            evidence=evidences,
            validation_codes=list(fobj.get("validation_codes") or []),
        )
    return ExtractionProviderResult(
        success=bool(payload.get("success")),
        provider_key=str(payload.get("provider_key") or "noop"),
        provider_version=str(payload.get("provider_version") or "1.0.0"),
        fields=fields,
        warnings=list(payload.get("warnings") or []),
        processing_duration_ms=int(payload.get("processing_duration_ms") or 0),
        retryable=bool(payload.get("retryable")),
        error_code=payload.get("error_code"),
        error_message_sanitized=payload.get("error_message_sanitized"),
        partially_completed=bool(payload.get("partially_completed")),
        confidence_score=payload.get("confidence_score"),
    )


class ValidateExtractionSchemaStep:
    step_key = STEP_VALIDATE_EXTRACTION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        draft_id = meta.get("_extraction_provider_draft_id")
        schema = meta.get("_extraction_schema") or {}
        if not draft_id:
            raise ProcessingPermanentError("provider_draft_missing", "Draft provider absent")
        obj = context.db.get(ElfisStorageObject, draft_id)
        if not obj:
            raise ProcessingPermanentError("provider_draft_missing", "Draft introuvable")
        payload = read_json_artifact(obj)
        result = _result_from_draft(payload)
        svc = DocumentExtractionService(context.db)
        validation = svc.validate_fields(
            str(schema.get("schema_key") or "generic_document_v1"),
            str(schema.get("schema_version") or "1"),
            result.fields,
        )
        # réécrit draft avec champs normalisés
        payload["fields"] = {k: v.to_public_dict() for k, v in validation.normalized_fields.items()}
        payload["validation"] = validation.to_summary_dict()
        limits = ExtractionLimits.from_settings()
        new_draft = store_provider_draft_artifact(
            context.db,
            organization_id=context.document.organization_id,
            job_id=context.job.id,
            provider_payload=payload,
            limits=limits,
        )
        meta["_extraction_provider_draft_id"] = new_draft.id
        meta["_extraction_validation_summary"] = {
            "valid": validation.valid,
            "missing_count": len(validation.missing_required_fields),
            "invalid_count": len(validation.invalid_fields),
            "requires_review": validation.requires_review,
            "codes_count": len(validation.validation_codes),
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary=meta["_extraction_validation_summary"],
        )


class PersistExtractionArtifactStep:
    step_key = STEP_PERSIST_EXTRACTION_ARTIFACT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        draft_id = meta.get("_extraction_provider_draft_id")
        schema = meta.get("_extraction_schema") or {}
        src = meta.get("_extraction_source") or {}
        eff = meta.get("_extraction_effective_type") or {}
        if not draft_id:
            raise ProcessingPermanentError("provider_draft_missing", "Draft absent")
        obj = context.db.get(ElfisStorageObject, draft_id)
        if not obj:
            raise ProcessingPermanentError("provider_draft_missing", "Draft introuvable")
        payload = read_json_artifact(obj)
        result = _result_from_draft(payload)
        svc = DocumentExtractionService(context.db)
        validation = svc.validate_fields(
            str(schema.get("schema_key") or "generic_document_v1"),
            str(schema.get("schema_version") or "1"),
            result.fields,
        )
        force = bool(meta.get("force_extraction"))
        ide = idempotency_hash_for(
            ocr_result_id=src.get("ocr_result_id"),
            options={"noop_mode": meta.get("noop_mode")},
        )
        row = svc.persist_result(
            document=context.document,
            version=context.version,
            job_id=context.job.id,
            ocr_result_id=src.get("ocr_result_id"),
            classification_id=schema.get("classification_id") or eff.get("classification_id"),
            schema_key=str(schema.get("schema_key")),
            schema_version=str(schema.get("schema_version") or "1"),
            provider_key=result.provider_key,
            provider_version=result.provider_version,
            selection_reason=schema.get("reason_code"),
            source_reason=src.get("reason_code"),
            effective_document_type=eff.get("type"),
            result=result,
            validation=validation,
            force=force,
            idempotency_hash=ide,
        )
        meta["_extraction_result_id"] = row.id
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "extraction_result_id": row.id,
                "status": row.status,
                "fields_count": row.fields_count,
                "missing_count": row.missing_required_fields_count,
                "requires_review": row.requires_review,
            },
        )


class FinalizeExtractionResultStep:
    step_key = STEP_FINALIZE_EXTRACTION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        eid = meta.get("_extraction_result_id")
        # nettoie refs draft (les blobs restent jusqu'à purge lifecycle)
        meta.pop("_extraction_source_artifact_id", None)
        # ne conserve pas de texte
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"extraction_result_id": eid, "finalized": True},
        )
