"""Étapes pipeline document_ocr_v1."""

from __future__ import annotations

import os
from pathlib import Path

from app.config import settings
from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingPermanentError, ProcessingRetryableError
from app.document_processing.ocr.exceptions import (
    OCRPermanentError,
    OCRRetryableError,
    OCRValidationError,
)
from app.document_processing.ocr.service import DocumentOCRService
from app.document_processing.types import (
    STEP_FINALIZE_OCR_RESULT,
    STEP_PERFORM_OCR,
    STEP_PERSIST_OCR_ARTIFACT,
    STEP_PREPARE_OCR_INPUT,
    STEP_SELECT_OCR_PROVIDER,
)

# Cache mémoire process-local — texte OCR jamais en metadata_json / logs
_OCR_RESULT_CACHE: dict[str, object] = {}


def _meta(ctx: ProcessingContext) -> dict:
    return dict(ctx.job.metadata_json or {})


def _set_meta(ctx: ProcessingContext, meta: dict) -> None:
    ctx.job.metadata_json = dict(meta)
    ctx.db.flush()


class SelectOCRProviderStep:
    step_key = STEP_SELECT_OCR_PROVIDER

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        if not getattr(settings, "document_ocr_enabled", False):
            # en tests on peut forcer via metadata
            if not (_meta(context).get("force_ocr_enabled") or _meta(context).get("noop_mode")):
                raise ProcessingPermanentError("ocr_disabled", "OCR désactivé")

        svc = DocumentOCRService(context.db)
        try:
            svc.assert_can_ocr(context.document, context.storage_object)
        except OCRValidationError as exc:
            if exc.code == "object_quarantined":
                return ProcessingStepResult(
                    success=False,
                    status="blocked",
                    error_code=exc.code,
                    error_message_sanitized=exc.message,
                    retryable=False,
                )
            raise ProcessingPermanentError(exc.code, exc.message) from exc

        mime = ""
        if context.storage_object:
            mime = (
                context.storage_object.mime_type_detected
                or context.storage_object.mime_type_declared
                or ""
            )
        mime = mime or context.version.mime_type or "application/octet-stream"
        try:
            selection = svc.select_provider(mime_type=mime)
        except OCRValidationError as exc:
            raise ProcessingPermanentError(exc.code, exc.message) from exc

        meta = _meta(context)
        meta["_ocr_selection"] = {
            "selected_provider": selection.selected_provider,
            "reason_code": selection.reason_code,
            "fallback_chain": selection.fallback_chain,
            "capabilities_checked": selection.capabilities_checked,
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "selected_provider": selection.selected_provider,
                "reason_code": selection.reason_code,
            },
        )


class PrepareOCRInputStep:
    step_key = STEP_PREPARE_OCR_INPUT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        selection = meta.get("_ocr_selection") or {}
        provider_key = selection.get("selected_provider")
        # noop : tempfile vide (aucun contenu lu)
        if provider_key == "noop":
            import tempfile as _tf

            fd, name = _tf.mkstemp(prefix="elfis-ocr-noop-", suffix=".bin")
            os.close(fd)
            meta["_ocr_temp_path"] = name
            _set_meta(context, meta)
            return ProcessingStepResult(
                success=True,
                status="completed",
                output_summary={"temp_prepared": True, "noop_empty": True},
            )

        if context.storage_object is None:
            raise ProcessingPermanentError("object_missing", "StorageObject absent")
        svc = DocumentOCRService(context.db)
        try:
            path = svc.prepare_temp(storage_object=context.storage_object)
        except ValueError as exc:
            raise ProcessingPermanentError(str(exc), "Préparation OCR refusée") from exc
        except Exception as exc:
            raise ProcessingRetryableError("prepare_failed", "Préparation fichier échouée") from exc

        meta["_ocr_temp_path"] = str(path)
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"temp_prepared": True},
        )


class PerformOCRStep:
    step_key = STEP_PERFORM_OCR

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        selection = meta.get("_ocr_selection") or {}
        provider_key = selection.get("selected_provider")
        temp = meta.get("_ocr_temp_path")
        if not provider_key or not temp:
            raise ProcessingPermanentError("ocr_state_missing", "État OCR incomplet")
        path = Path(temp)
        svc = DocumentOCRService(context.db)
        noop_mode = meta.get("noop_mode")
        try:
            # propage options de test bornées (pages simulées)
            from app.document_processing.ocr.provider import OCRRequest as _OR
            from app.document_processing.ocr.provider_registry import get_ocr_provider_registry

            provider = get_ocr_provider_registry().get(provider_key)
            langs = [
                x.strip()
                for x in str(
                    getattr(settings, "document_ocr_default_languages", "fra,eng") or ""
                ).split(",")
                if x.strip()
            ]
            opts = {}
            if noop_mode:
                opts["noop_mode"] = noop_mode
            if meta.get("noop_pages") is not None:
                opts["noop_pages"] = meta.get("noop_pages")
            result = await provider.recognize(
                _OR(
                    document_id=context.document.id,
                    document_version_id=context.version.id,
                    mime_type=(
                        (context.storage_object.mime_type_detected if context.storage_object else None)
                        or (context.storage_object.mime_type_declared if context.storage_object else None)
                        or context.version.mime_type
                        or "application/pdf"
                    ),
                    language_hints=langs,
                    temp_path=path,
                    options=opts,
                    correlation_id=context.job.correlation_id,
                    max_pages=int(getattr(settings, "document_ocr_max_pages", 50) or 50),
                    max_page_characters=int(
                        getattr(settings, "document_ocr_max_page_characters", 50_000) or 50_000
                    ),
                    max_text_characters=int(
                        getattr(settings, "document_ocr_max_text_characters", 500_000) or 500_000
                    ),
                    noop_mode=noop_mode,
                )
            )
        except OCRRetryableError as exc:
            raise ProcessingRetryableError(exc.code, exc.message) from exc
        except OCRPermanentError as exc:
            raise ProcessingPermanentError(exc.code, exc.message) from exc
        finally:
            try:
                if path.is_file():
                    path.unlink()
            except Exception:
                pass
            meta.pop("_ocr_temp_path", None)
            _set_meta(context, meta)

        # résumé sans texte dans metadata ; résultat complet en cache mémoire
        meta["_ocr_provider_result"] = {
            "success": result.success,
            "provider_key": result.provider_key,
            "provider_version": result.provider_version,
            "extraction_method": result.extraction_method,
            "page_count": len(result.pages),
            "warnings": list(result.warnings or [])[:20],
            "retryable": result.retryable,
            "error_code": result.error_code,
            "error_message_sanitized": result.error_message_sanitized,
            "partially_completed": result.partially_completed,
            "processing_duration_ms": result.processing_duration_ms,
            "detected_languages": list(result.detected_languages or [])[:10],
        }
        _OCR_RESULT_CACHE[context.job.id] = result
        _set_meta(context, meta)
        if not result.success:
            if result.retryable:
                raise ProcessingRetryableError(
                    result.error_code or "ocr_failed",
                    result.error_message_sanitized or "OCR échoué",
                )
            raise ProcessingPermanentError(
                result.error_code or "ocr_failed",
                result.error_message_sanitized or "OCR échoué",
            )
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "provider_key": result.provider_key,
                "page_count": len(result.pages),
                "extraction_method": result.extraction_method,
                "duration_ms": result.processing_duration_ms,
            },
        )


class PersistOCRArtifactStep:
    step_key = STEP_PERSIST_OCR_ARTIFACT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        from app.document_processing.ocr.provider import OCRProviderResult

        meta = _meta(context)
        raw = dict(meta.get("_ocr_provider_result") or {})
        selection = meta.get("_ocr_selection") or {}
        cached = _OCR_RESULT_CACHE.pop(context.job.id, None)
        force = bool(meta.get("force_ocr"))

        if isinstance(cached, OCRProviderResult):
            result = cached
        else:
            # fallback sans texte (ne devrait pas arriver en worker unique)
            result = OCRProviderResult(
                success=bool(raw.get("success")),
                provider_key=str(
                    raw.get("provider_key") or selection.get("selected_provider") or "noop"
                ),
                provider_version=str(raw.get("provider_version") or "1.0.0"),
                extraction_method=str(raw.get("extraction_method") or "unknown"),
                pages=[],
                detected_languages=list(raw.get("detected_languages") or []),
                warnings=list(raw.get("warnings") or []),
                processing_duration_ms=int(raw.get("processing_duration_ms") or 0),
                partially_completed=bool(raw.get("partially_completed")),
                error_code=raw.get("error_code"),
                error_message_sanitized=raw.get("error_message_sanitized"),
            )

        svc = DocumentOCRService(context.db)
        row = svc.persist_provider_result(
            document=context.document,
            version=context.version,
            job_id=context.job.id,
            provider_key=result.provider_key or selection.get("selected_provider") or "noop",
            provider_version=result.provider_version or "1.0.0",
            selection_reason=selection.get("reason_code"),
            result=result,
            force=force,
        )
        meta["_ocr_result_id"] = row.id
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "ocr_result_id": row.id,
                "status": row.status,
                "page_count": row.page_count,
                "text_length": row.text_length,
                "requires_review": row.requires_review,
            },
        )


class FinalizeOCRResultStep:
    step_key = STEP_FINALIZE_OCR_RESULT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        ocr_id = meta.get("_ocr_result_id")
        # nettoie chemins / pages
        meta.pop("_ocr_temp_path", None)
        if isinstance(meta.get("_ocr_provider_result"), dict):
            meta["_ocr_provider_result"].pop("_pages", None)
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"ocr_result_id": ocr_id, "finalized": True},
        )
