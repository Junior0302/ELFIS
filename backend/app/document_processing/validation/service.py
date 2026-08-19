"""BusinessValidationService — règles métier documentaires ELFIS (pas comptables)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.extraction.models import ElfisDocumentExtractionResult
from app.document_processing.extraction.service import DocumentExtractionService
from app.document_processing.extraction.types import ExtractionResultStatus
from app.document_processing.service import DocumentProcessingService
from app.document_processing.validation import metrics as bv_metrics
from app.document_processing.validation.exceptions import (
    BusinessValidationAccessDeniedError,
    BusinessValidationNotFoundError,
    BusinessValidationValidationError,
)
from app.document_processing.validation.models import (
    ElfisDocumentBusinessValidation,
    ElfisDocumentValidationIssue,
)
from app.document_processing.validation.pipeline import (
    build_validation_artifact,
    delete_validation_artifact,
    store_validation_artifact,
)
from app.document_processing.validation.policies import BusinessValidationAccessPolicy, ValidationLimits
from app.document_processing.validation.repository import BusinessValidationRepository
from app.document_processing.validation.rule_base import RuleContext
from app.document_processing.validation.rule_registry import get_business_validation_rule_registry
from app.document_processing.validation.sanitization import sanitize_issue_parameters
from app.document_processing.validation.types import (
    BusinessValidationStatus,
    PIPELINE_BUSINESS_VALIDATION_V1,
    ResolutionType,
)
from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion, ElfisStorageObject

logger = logging.getLogger(__name__)


class EffectiveExtractionSelectionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._limits = ValidationLimits.from_settings()

    def select(
        self,
        *,
        organization_id: int,
        document_id: str,
        document_version_id: str,
    ) -> ElfisDocumentExtractionResult:
        rows = (
            self._db.query(ElfisDocumentExtractionResult)
            .filter(
                ElfisDocumentExtractionResult.organization_id == organization_id,
                ElfisDocumentExtractionResult.document_id == document_id,
                ElfisDocumentExtractionResult.document_version_id == document_version_id,
            )
            .order_by(ElfisDocumentExtractionResult.created_at.desc())
            .all()
        )
        if not rows:
            raise BusinessValidationValidationError("extraction_missing", "Aucune extraction")

        require_confirmed = self._limits.require_confirmed_extraction
        for row in rows:
            if row.status == ExtractionResultStatus.REJECTED.value:
                continue
            if row.status == ExtractionResultStatus.SUPERSEDED.value:
                continue
            if not row.result_artifact_storage_object_id:
                continue
            if row.status == ExtractionResultStatus.CONFIRMED.value:
                return row
        if require_confirmed:
            raise BusinessValidationValidationError(
                "extraction_not_confirmed",
                "Extraction confirmée requise",
            )
        for status in (
            ExtractionResultStatus.COMPLETED.value,
            ExtractionResultStatus.PARTIALLY_COMPLETED.value,
            ExtractionResultStatus.INVALID.value,
        ):
            for row in rows:
                if row.status == status and row.result_artifact_storage_object_id:
                    return row
        raise BusinessValidationValidationError("extraction_unavailable", "Extraction indisponible")


class DocumentBusinessValidationService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = BusinessValidationRepository(db)
        self._audit = audit_logger
        self._limits = ValidationLimits.from_settings()
        self._policy = BusinessValidationAccessPolicy()
        self._rules = get_business_validation_rule_registry()

    def list_rule_sets_public(self) -> list[dict]:
        return self._rules.list_public()

    def select_extraction(self, **kwargs) -> ElfisDocumentExtractionResult:
        return EffectiveExtractionSelectionService(self._db).select(**kwargs)

    def load_extraction_fields(
        self, *, extraction_id: str, organization_id: int, document_version_id: str
    ) -> tuple[dict[str, Any], ElfisDocumentExtractionResult]:
        extr = DocumentExtractionService(self._db, audit_logger=self._audit)
        data, row = extr.open_content(extraction_id, organization_id, platform=False)
        if row.document_version_id != document_version_id:
            raise BusinessValidationValidationError("extraction_version_mismatch", "Mauvaise version")
        import json

        payload = json.loads(data.decode("utf-8"))
        return dict(payload.get("fields") or {}), row

    def run_rules(
        self,
        *,
        schema_key: str,
        document_type: str | None,
        fields: dict[str, Any],
        extraction_status: str | None,
        extraction_requires_review: bool,
        classification_ambiguous: bool = False,
    ):
        rule_set = self._rules.select_for_schema(schema_key)
        ctx = RuleContext(
            schema_key=schema_key,
            document_type=document_type,
            fields=fields,
            amount_tolerance=self._limits.amount_tolerance,
            percentage_tolerance=self._limits.percentage_tolerance,
            extraction_status=extraction_status,
            extraction_requires_review=extraction_requires_review,
            classification_ambiguous=classification_ambiguous,
        )
        issues = self._rules.execute(rule_set, ctx)
        return rule_set, issues

    def persist_result(
        self,
        *,
        document: ElfisDocumentRecord,
        version: ElfisDocumentVersion,
        extraction: ElfisDocumentExtractionResult,
        job_id: str | None,
        rule_set_key: str,
        rule_set_version: str,
        issues_drafts: list,
        force: bool = False,
        classification_id: str | None = None,
    ) -> ElfisDocumentBusinessValidation:
        if force:
            self._repo.supersede_active(
                document_version_id=version.id,
                extraction_result_id=extraction.id,
            )

        blocking = [i for i in issues_drafts if i.blocking and i.severity in ("error", "critical")]
        warnings = [i for i in issues_drafts if i.severity == "warning"]
        infos = [i for i in issues_drafts if i.severity == "info"]
        requires = bool(warnings) or bool(extraction.requires_review)

        if blocking:
            status = BusinessValidationStatus.INVALID.value
            valid = False
            if any(i.issue_code.endswith("REVIEW") or "REVIEW" in i.issue_code for i in issues_drafts):
                status = BusinessValidationStatus.REVIEW_REQUIRED.value
                requires = True
        elif warnings:
            status = BusinessValidationStatus.VALID_WITH_WARNINGS.value
            valid = True
            requires = True
        else:
            status = BusinessValidationStatus.VALID.value
            valid = True

        # EXTRACTION_INVALID always invalid
        if any(i.issue_code == "EXTRACTION_INVALID_BLOCK" for i in issues_drafts):
            status = BusinessValidationStatus.INVALID.value
            valid = False

        now = datetime.utcnow()
        row_id = str(uuid4())
        issue_payloads = [
            {
                "rule_key": i.rule_key,
                "severity": i.severity,
                "issue_code": i.issue_code,
                "field_paths": list(i.field_paths or [])[:20],
                "blocking": i.blocking,
            }
            for i in issues_drafts
        ]
        raw, checksum = build_validation_artifact(
            document_version_id=version.id,
            extraction_result_id=extraction.id,
            rule_set_key=rule_set_key,
            rule_set_version=rule_set_version,
            status=status,
            issues=issue_payloads,
        )
        artifact = store_validation_artifact(
            self._db,
            organization_id=document.organization_id,
            validation_id=row_id,
            content=raw,
            checksum=checksum,
            limits=self._limits,
        )
        row = ElfisDocumentBusinessValidation(
            id=row_id,
            organization_id=document.organization_id,
            document_id=document.id,
            document_version_id=version.id,
            extraction_result_id=extraction.id,
            classification_id=classification_id or extraction.classification_id,
            processing_job_id=job_id,
            rule_set_key=rule_set_key,
            rule_set_version=rule_set_version,
            status=status,
            valid=valid,
            blocking_issue_count=len(blocking),
            warning_count=len(warnings),
            info_count=len(infos),
            requires_review=requires,
            validation_artifact_storage_object_id=artifact.id,
            artifact_checksum_sha256=checksum,
            started_at=now,
            completed_at=now,
        )
        self._repo.add_result(row, commit=False)
        for draft in issues_drafts:
            self._repo.add_issue(
                ElfisDocumentValidationIssue(
                    id=str(uuid4()),
                    business_validation_id=row.id,
                    rule_key=draft.rule_key,
                    rule_version=draft.rule_version,
                    severity=draft.severity,
                    field_paths_json=list(draft.field_paths or [])[:20],
                    issue_code=draft.issue_code,
                    message_code=draft.message_code or draft.issue_code,
                    parameters_json=sanitize_issue_parameters(draft.parameters),
                    blocking=bool(draft.blocking),
                ),
                commit=False,
            )
        self._db.commit()
        self._db.refresh(row)
        bv_metrics.incr("business_validation_completed")
        audit_m = (
            "record_document_business_validation_completed"
            if valid
            else (
                "record_document_business_validation_review_required"
                if status == BusinessValidationStatus.REVIEW_REQUIRED.value
                else "record_document_business_validation_invalid"
            )
        )
        self._safe_audit(
            audit_m,
            validation_id=row.id,
            document_id=document.id,
            version_id=version.id,
            extraction_result_id=extraction.id,
            organization_id=document.organization_id,
            job_id=job_id,
            rule_set=rule_set_key,
            status=status,
            blocking_count=row.blocking_issue_count,
            warning_count=row.warning_count,
        )
        return row

    def get_for_org(self, validation_id: str, organization_id: int) -> ElfisDocumentBusinessValidation:
        row = self._repo.get(validation_id)
        if not row or row.organization_id != organization_id:
            raise BusinessValidationNotFoundError("not_found", "Validation introuvable")
        return row

    def get_platform(self, validation_id: str) -> ElfisDocumentBusinessValidation:
        row = self._repo.get(validation_id)
        if not row:
            raise BusinessValidationNotFoundError("not_found", "Validation introuvable")
        return row

    def list_results(self, **kwargs):
        return self._repo.list_results(**kwargs)

    def list_issues(self, validation_id: str):
        return self._repo.list_issues(validation_id)

    def confirm(
        self,
        validation_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentBusinessValidation:
        row = self.get_platform(validation_id) if platform else self.get_for_org(validation_id, organization_id)
        open_blocking = [
            i
            for i in self._repo.list_issues(row.id)
            if i.blocking and not i.resolved
        ]
        if open_blocking:
            raise BusinessValidationValidationError(
                "blocking_unresolved",
                "Issues bloquantes non résolues",
            )
        if row.status == BusinessValidationStatus.VALID.value and not row.requires_review:
            return row
        # confirmation humaine : valide avec warnings acceptées
        if row.status in (
            BusinessValidationStatus.VALID.value,
            BusinessValidationStatus.VALID_WITH_WARNINGS.value,
            BusinessValidationStatus.REVIEW_REQUIRED.value,
        ):
            row.status = BusinessValidationStatus.VALID.value
            row.valid = True
            row.requires_review = False
            row.updated_at = datetime.utcnow()
            self._db.commit()
            self._db.refresh(row)
            self._safe_audit(
                "record_document_business_validation_confirmed",
                validation_id=row.id,
                document_id=row.document_id,
                version_id=row.document_version_id,
                organization_id=row.organization_id,
                status=row.status,
                actor_user_id=actor_user_id,
            )
            return row
        raise BusinessValidationValidationError("not_confirmable", "Validation non confirmable")

    def resolve_issue(
        self,
        validation_id: str,
        issue_id: str,
        organization_id: int,
        *,
        resolution_type: str,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentValidationIssue:
        row = self.get_platform(validation_id) if platform else self.get_for_org(validation_id, organization_id)
        issue = self._repo.get_issue(issue_id)
        if not issue or issue.business_validation_id != row.id:
            raise BusinessValidationNotFoundError("issue_not_found", "Issue introuvable")
        if issue.resolved:
            return issue
        # erreur bloquante : acknowledged interdit
        if issue.blocking and resolution_type == ResolutionType.ACKNOWLEDGED.value:
            raise BusinessValidationValidationError(
                "blocking_ack_forbidden",
                "Issue bloquante non résoluble par acknowledgement",
            )
        allowed = {r.value for r in ResolutionType}
        if resolution_type not in allowed:
            raise BusinessValidationValidationError("resolution_unknown", "Résolution inconnue")
        if issue.blocking and resolution_type not in (
            ResolutionType.FALSE_POSITIVE.value,
            ResolutionType.CORRECTED_EXTRACTION.value,
            ResolutionType.REJECTED_DOCUMENT.value,
        ):
            if resolution_type == ResolutionType.ACCEPTED_WARNING.value:
                raise BusinessValidationValidationError(
                    "blocking_not_warning",
                    "Issue bloquante non acceptée comme warning",
                )
        issue.resolved = True
        issue.resolution_type = resolution_type
        issue.resolved_by_user_id = actor_user_id
        issue.resolved_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(issue)
        self._safe_audit(
            "record_document_validation_issue_resolved",
            validation_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            issue_code=issue.issue_code,
            resolution_type=resolution_type,
            actor_user_id=actor_user_id,
        )
        return issue

    def request_revalidate(
        self,
        validation_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
    ):
        row = self.get_platform(validation_id) if platform else self.get_for_org(validation_id, organization_id)
        pipe = (
            getattr(settings, "document_business_validation_default_pipeline", None)
            or PIPELINE_BUSINESS_VALIDATION_V1
        )
        return DocumentProcessingService(self._db, audit_logger=self._audit).create_job(
            organization_id=row.organization_id,
            document_id=row.document_id,
            document_version_id=row.document_version_id,
            pipeline_key=pipe,
            metadata={
                "force_business_validation": True,
                "force_business_validation_enabled": True,
                "from_validation_id": row.id,
            },
            requested_by_user_id=actor_user_id,
        )

    def request_validate(
        self,
        *,
        organization_id: int,
        document_id: str,
        document_version_id: str | None = None,
        actor_user_id: int | None = None,
        force: bool = False,
    ):
        from app.storage.storage_models import ElfisDocumentRecord, ElfisDocumentVersion

        doc = self._db.get(ElfisDocumentRecord, document_id)
        if not doc or doc.organization_id != organization_id:
            raise BusinessValidationNotFoundError("document_not_found", "Document introuvable")
        self._policy.assert_document_ok(doc, for_mutate=True)
        version_id = document_version_id or doc.current_version_id
        if not version_id:
            raise BusinessValidationValidationError("version_missing", "Version absente")
        ver = self._db.get(ElfisDocumentVersion, version_id)
        if not ver or ver.document_id != doc.id:
            raise BusinessValidationValidationError("version_invalid", "Version invalide")
        pipe = (
            getattr(settings, "document_business_validation_default_pipeline", None)
            or PIPELINE_BUSINESS_VALIDATION_V1
        )
        self._safe_audit(
            "record_document_business_validation_started",
            document_id=doc.id,
            version_id=version_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        return DocumentProcessingService(self._db, audit_logger=self._audit).create_job(
            organization_id=organization_id,
            document_id=doc.id,
            document_version_id=version_id,
            pipeline_key=pipe,
            metadata={
                "force_business_validation": force,
                "force_business_validation_enabled": True,
            },
            requested_by_user_id=actor_user_id,
        )

    def assert_can_validate(self, document: ElfisDocumentRecord, storage_object: ElfisStorageObject | None) -> None:
        quarantined = bool(storage_object and storage_object.status == "quarantined")
        self._policy.assert_can_validate(document, quarantined=quarantined)

    def purge_artifacts_for_document(
        self, document_id: str, *, organization_id: int, legal_hold_active: bool = False
    ) -> int:
        if legal_hold_active:
            raise BusinessValidationValidationError("legal_hold", "Legal hold bloque purge validation")
        deleted = 0
        for row in self._repo.list_for_document(document_id):
            if row.organization_id != organization_id:
                continue
            oid = row.validation_artifact_storage_object_id
            if oid:
                obj = self._db.get(ElfisStorageObject, oid)
                if obj:
                    try:
                        delete_validation_artifact(obj)
                    except Exception:
                        pass
                    obj.status = "purged"
                row.validation_artifact_storage_object_id = None
                deleted += 1
            row.status = BusinessValidationStatus.SUPERSEDED.value
            row.updated_at = datetime.utcnow()
        self._db.flush()
        return deleted

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**{k: v for k, v in kwargs.items() if v is not None})
        except Exception:
            logger.debug("bv_audit_failed", exc_info=True)
