"""Étapes pipeline document_business_validation_v1."""

from __future__ import annotations

from app.config import settings
from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.exceptions import ProcessingPermanentError
from app.document_processing.validation.exceptions import BusinessValidationValidationError
from app.document_processing.validation.pipeline import read_json_artifact, store_json_draft
from app.document_processing.validation.policies import ValidationLimits
from app.document_processing.validation.service import DocumentBusinessValidationService
from app.document_processing.validation.types import (
    STEP_FINALIZE_BUSINESS_VALIDATION,
    STEP_LOAD_EXTRACTION_CONTENT,
    STEP_PERFORM_BUSINESS_VALIDATION,
    STEP_PERSIST_VALIDATION_ARTIFACT,
    STEP_SELECT_BUSINESS_RULE_SET,
    STEP_SELECT_EFFECTIVE_EXTRACTION,
)
from app.storage.storage_models import ElfisStorageObject


def _meta(ctx: ProcessingContext) -> dict:
    return dict(ctx.job.metadata_json or {})


def _set_meta(ctx: ProcessingContext, meta: dict) -> None:
    ctx.job.metadata_json = dict(meta)
    ctx.db.flush()


class SelectEffectiveExtractionStep:
    step_key = STEP_SELECT_EFFECTIVE_EXTRACTION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        if not getattr(settings, "document_business_validation_enabled", False):
            if not meta.get("force_business_validation_enabled"):
                raise ProcessingPermanentError("validation_disabled", "Validation métier désactivée")
        svc = DocumentBusinessValidationService(context.db)
        try:
            svc.assert_can_validate(context.document, context.storage_object)
            extr = svc.select_extraction(
                organization_id=context.document.organization_id,
                document_id=context.document.id,
                document_version_id=context.version.id,
            )
        except BusinessValidationValidationError as exc:
            if exc.code == "object_quarantined":
                return ProcessingStepResult(
                    success=False,
                    status="blocked",
                    error_code=exc.code,
                    error_message_sanitized=exc.message,
                    retryable=False,
                )
            raise ProcessingPermanentError(exc.code, exc.message) from exc
        meta["_bv_extraction"] = {
            "extraction_result_id": extr.id,
            "schema_key": extr.schema_key,
            "schema_version": extr.schema_version,
            "status": extr.status,
            "requires_review": extr.requires_review,
            "classification_id": extr.classification_id,
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "extraction_result_id": extr.id,
                "schema_key": extr.schema_key,
                "status": extr.status,
            },
        )


class LoadExtractionContentStep:
    step_key = STEP_LOAD_EXTRACTION_CONTENT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        info = meta.get("_bv_extraction") or {}
        eid = info.get("extraction_result_id")
        if not eid:
            raise ProcessingPermanentError("extraction_missing", "Extraction absente")
        svc = DocumentBusinessValidationService(context.db)
        try:
            fields, _row = svc.load_extraction_fields(
                extraction_id=eid,
                organization_id=context.document.organization_id,
                document_version_id=context.version.id,
            )
        except BusinessValidationValidationError as exc:
            raise ProcessingPermanentError(exc.code, exc.message) from exc
        limits = ValidationLimits.from_settings()
        draft = store_json_draft(
            context.db,
            organization_id=context.document.organization_id,
            job_id=context.job.id,
            payload={"schema": "bv_extraction_draft_v1", "fields": fields},
            limits=limits,
            purpose="bv_extraction_draft",
        )
        meta["_bv_extraction_draft_id"] = draft.id
        meta["_bv_fields_count"] = len(fields)
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"fields_count": len(fields), "loaded": True},
        )


class SelectBusinessRuleSetStep:
    step_key = STEP_SELECT_BUSINESS_RULE_SET

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        from app.document_processing.validation.rule_registry import get_business_validation_rule_registry

        meta = _meta(context)
        info = meta.get("_bv_extraction") or {}
        schema_key = str(info.get("schema_key") or "generic_document_v1")
        rule_set = get_business_validation_rule_registry().select_for_schema(schema_key)
        meta["_bv_rule_set"] = {"key": rule_set.key, "version": rule_set.version}
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"rule_set_key": rule_set.key, "rule_set_version": rule_set.version},
        )


class PerformBusinessValidationStep:
    step_key = STEP_PERFORM_BUSINESS_VALIDATION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        draft_id = meta.get("_bv_extraction_draft_id")
        info = meta.get("_bv_extraction") or {}
        rs = meta.get("_bv_rule_set") or {}
        if not draft_id:
            raise ProcessingPermanentError("draft_missing", "Draft extraction absent")
        obj = context.db.get(ElfisStorageObject, draft_id)
        if not obj:
            raise ProcessingPermanentError("draft_missing", "Draft introuvable")
        payload = read_json_artifact(obj)
        fields = dict(payload.get("fields") or {})
        eff = meta.get("_extraction_effective_type") or {}
        svc = DocumentBusinessValidationService(context.db)
        rule_set, issues = svc.run_rules(
            schema_key=str(info.get("schema_key") or "generic_document_v1"),
            document_type=eff.get("type"),
            fields=fields,
            extraction_status=info.get("status"),
            extraction_requires_review=bool(info.get("requires_review")),
            classification_ambiguous=bool(eff.get("requires_review") and not eff.get("confirmed")),
        )
        # sérialise issues dans draft (sans valeurs)
        issue_dicts = [
            {
                "rule_key": i.rule_key,
                "rule_version": i.rule_version,
                "severity": i.severity,
                "issue_code": i.issue_code,
                "field_paths": i.field_paths,
                "parameters": i.parameters,
                "blocking": i.blocking,
                "message_code": i.message_code,
            }
            for i in issues
        ]
        limits = ValidationLimits.from_settings()
        draft = store_json_draft(
            context.db,
            organization_id=context.document.organization_id,
            job_id=context.job.id,
            payload={
                "schema": "bv_issues_draft_v1",
                "rule_set_key": rule_set.key,
                "rule_set_version": rule_set.version,
                "issues": issue_dicts,
                "fields": fields,
            },
            limits=limits,
            purpose="bv_issues_draft",
        )
        meta["_bv_issues_draft_id"] = draft.id
        meta["_bv_issue_summary"] = {
            "blocking": sum(1 for i in issues if i.blocking),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
            "total": len(issues),
            "rule_set_key": rs.get("key") or rule_set.key,
        }
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary=meta["_bv_issue_summary"],
        )


class PersistValidationArtifactStep:
    step_key = STEP_PERSIST_VALIDATION_ARTIFACT

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        from app.document_processing.extraction.models import ElfisDocumentExtractionResult
        from app.document_processing.validation.rule_base import ValidationIssueDraft

        meta = _meta(context)
        draft_id = meta.get("_bv_issues_draft_id")
        info = meta.get("_bv_extraction") or {}
        if not draft_id:
            raise ProcessingPermanentError("issues_draft_missing", "Draft issues absent")
        obj = context.db.get(ElfisStorageObject, draft_id)
        if not obj:
            raise ProcessingPermanentError("issues_draft_missing", "Draft introuvable")
        payload = read_json_artifact(obj)
        issues = [
            ValidationIssueDraft(
                rule_key=str(i.get("rule_key")),
                rule_version=str(i.get("rule_version") or "1"),
                severity=str(i.get("severity") or "info"),
                issue_code=str(i.get("issue_code")),
                field_paths=list(i.get("field_paths") or []),
                parameters=dict(i.get("parameters") or {}),
                blocking=bool(i.get("blocking")),
                message_code=i.get("message_code"),
            )
            for i in (payload.get("issues") or [])
            if isinstance(i, dict)
        ]
        extr = context.db.get(ElfisDocumentExtractionResult, info.get("extraction_result_id"))
        if not extr:
            raise ProcessingPermanentError("extraction_missing", "Extraction absente")
        svc = DocumentBusinessValidationService(context.db)
        row = svc.persist_result(
            document=context.document,
            version=context.version,
            extraction=extr,
            job_id=context.job.id,
            rule_set_key=str(payload.get("rule_set_key") or "generic_document_validation_v1"),
            rule_set_version=str(payload.get("rule_set_version") or "1"),
            issues_drafts=issues,
            force=bool(meta.get("force_business_validation")),
            classification_id=info.get("classification_id"),
        )
        meta["_bv_validation_id"] = row.id
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "validation_id": row.id,
                "status": row.status,
                "valid": row.valid,
                "blocking_issue_count": row.blocking_issue_count,
                "warning_count": row.warning_count,
                "requires_review": row.requires_review,
            },
        )


class FinalizeBusinessValidationStep:
    step_key = STEP_FINALIZE_BUSINESS_VALIDATION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = _meta(context)
        vid = meta.get("_bv_validation_id")
        meta.pop("_bv_extraction_draft_id", None)
        _set_meta(context, meta)
        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={"validation_id": vid, "finalized": True},
        )


__all__ = [
    "SelectEffectiveExtractionStep",
    "LoadExtractionContentStep",
    "SelectBusinessRuleSetStep",
    "PerformBusinessValidationStep",
    "PersistValidationArtifactStep",
    "FinalizeBusinessValidationStep",
]
