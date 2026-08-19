"""Service classification — persist, revue, reclassify. Classifiers n'écrivent pas en DB."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.document_processing.classification.classifiers.base import (
    ClassificationContext,
    DocumentClassificationResult,
)
from app.document_processing.classification.classifiers.composite import CompositeDocumentClassifier
from app.document_processing.classification.exceptions import (
    ClassificationAccessDeniedError,
    ClassificationNotFoundError,
    ClassificationValidationError,
)
from app.document_processing.classification.models import ElfisDocumentClassification
from app.document_processing.classification.repository import ClassificationRepository
from app.document_processing.classification.resolution import DocumentTypeResolutionService
from app.document_processing.classification.sanitization import (
    round_score,
    sanitize_evidence_items,
    sanitize_reason,
)
from app.document_processing.classification.scoring import ClassificationScoringPolicy
from app.document_processing.classification.taxonomy import get_document_type_registry
from app.document_processing.classification.types import (
    CLASSIFIER_COMPOSITE_KEY,
    CLASSIFIER_COMPOSITE_VERSION,
    ClassificationStatus,
    PIPELINE_CLASSIFICATION_V1,
)
from app.document_processing.service import DocumentProcessingService
from app.storage.storage_models import (
    ElfisDocumentLink,
    ElfisDocumentRecord,
    ElfisDocumentVersion,
    ElfisStorageObject,
)

logger = logging.getLogger(__name__)


class DocumentClassificationService:
    def __init__(self, db: Session, *, audit_logger: Any | None = None) -> None:
        self._db = db
        self._repo = ClassificationRepository(db)
        self._audit = audit_logger
        self._registry = get_document_type_registry()
        self._scoring = ClassificationScoringPolicy.from_settings()
        self._classifier = CompositeDocumentClassifier(self._scoring)
        self._resolution = DocumentTypeResolutionService(db, audit_logger=audit_logger)

    def get_for_org(self, classification_id: str, organization_id: int) -> ElfisDocumentClassification:
        row = self._repo.get(classification_id)
        if not row or row.organization_id != organization_id:
            raise ClassificationAccessDeniedError("classification_access_denied", "Introuvable")
        return row

    def get_platform(self, classification_id: str) -> ElfisDocumentClassification:
        row = self._repo.get(classification_id)
        if not row:
            raise ClassificationNotFoundError("not_found", "Introuvable")
        return row

    def list_classifications(self, **kwargs):
        return self._repo.list_classifications(**kwargs)

    def taxonomy(self) -> list[dict[str, Any]]:
        return [
            {
                "key": t.key,
                "label": t.label,
                "category": t.category,
                "description": t.description,
                "sensitive": t.sensitive,
                "processing_policy": t.processing_policy,
                "aliases": list(t.aliases),
            }
            for t in self._registry.list_types()
        ]

    async def run_classifier(
        self,
        *,
        document: ElfisDocumentRecord,
        version: ElfisDocumentVersion,
        storage_object: ElfisStorageObject | None,
        job_id: str | None = None,
    ) -> DocumentClassificationResult:
        links = (
            self._db.query(ElfisDocumentLink)
            .filter(ElfisDocumentLink.document_id == document.id)
            .limit(50)
            .all()
        )
        ctx = ClassificationContext(
            db=self._db,
            document=document,
            version=version,
            storage_object=storage_object,
            links=list(links),
            job_id=job_id,
            organization_id=document.organization_id,
        )
        self._safe_audit(
            "record_document_classification_started",
            document_id=document.id,
            version_id=version.id,
            organization_id=document.organization_id,
            job_id=job_id,
            classifier_key=self._classifier.classifier_key,
            classifier_version=self._classifier.classifier_version,
        )
        try:
            return await self._classifier.classify(ctx)
        except Exception as exc:
            self._safe_audit(
                "record_document_classification_failed",
                document_id=document.id,
                version_id=version.id,
                organization_id=document.organization_id,
                job_id=job_id,
                classifier_key=self._classifier.classifier_key,
            )
            raise ClassificationValidationError("classification_failed", str(exc)[:120]) from exc

    def persist_result(
        self,
        *,
        document: ElfisDocumentRecord,
        version: ElfisDocumentVersion,
        result: DocumentClassificationResult,
        job_id: str | None = None,
        force: bool = False,
        source: str = "pipeline",
    ) -> ElfisDocumentClassification:
        if not getattr(settings, "document_classification_enabled", True):
            raise ClassificationValidationError("classification_disabled", "Classification désactivée")

        key = result.classifier_key or CLASSIFIER_COMPOSITE_KEY
        ver = result.classifier_version or CLASSIFIER_COMPOSITE_VERSION

        if not force:
            existing = self._repo.find_active(
                document_version_id=version.id,
                classifier_key=key,
                classifier_version=ver,
            )
            if existing:
                return existing

        self._repo.supersede_active(
            document_version_id=version.id,
            classifier_key=key,
        )

        predicted = self._registry.resolve_key(result.predicted_type) or "unknown"
        max_ev = int(getattr(settings, "document_classification_evidence_max_items", 20) or 20)
        evidence = sanitize_evidence_items(
            [{"code": e.code, "detail": e.detail, "weight": e.weight} for e in result.evidence],
            max_items=max_ev,
        )
        alts = [
            {"type": a.type_key, "score": round_score(a.score)}
            for a in result.alternatives[: self._scoring.max_alternatives]
        ]
        score = round_score(result.confidence_score)
        requires = bool(result.requires_review)
        if self._scoring.is_auto_confirmable(score, ambiguous=predicted == "invoice"):
            requires = False

        row = ElfisDocumentClassification(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=job_id,
            organization_id=document.organization_id,
            classifier_key=key,
            classifier_version=ver,
            predicted_type=predicted,
            confidence_score=score,
            status=ClassificationStatus.PROPOSED.value,
            requires_review=requires,
            evidence_json=evidence,
            alternatives_json=alts,
            source=source[:32],
        )

        # auto-confirm si politique
        if self._scoring.is_auto_confirmable(score, ambiguous=predicted in ("invoice", "unknown")):
            row.status = ClassificationStatus.CONFIRMED.value
            row.confirmed_type = predicted
            row.confirmed_at = datetime.utcnow()
            row.requires_review = False

        self._repo.add(row, commit=True)
        self._safe_audit(
            "record_document_classification_proposed",
            classification_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            job_id=job_id,
            classifier_key=key,
            classifier_version=ver,
            predicted_type=predicted,
            score=score,
            requires_review=row.requires_review,
            evidence_codes=[e.get("code") for e in evidence if e.get("code")],
        )
        self._resolution.maybe_sync_document_type(row)
        return row

    def confirm(
        self,
        classification_id: str,
        organization_id: int,
        *,
        confirmed_type: str,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentClassification:
        row = self.get_platform(classification_id) if platform else self.get_for_org(classification_id, organization_id)
        resolved = self._registry.resolve_key(confirmed_type)
        if not resolved or resolved == "unknown":
            # unknown autorisé si explicitement choisi
            if not self._registry.is_known(confirmed_type):
                raise ClassificationValidationError("invalid_type", "Type inconnu")
            resolved = self._registry.resolve_key(confirmed_type) or confirmed_type

        if row.status == ClassificationStatus.CONFIRMED.value and row.confirmed_type == resolved:
            return row  # idempotent
        if row.status in (ClassificationStatus.SUPERSEDED.value, ClassificationStatus.FAILED.value):
            raise ClassificationValidationError("invalid_status", "Classification non revueable")

        now = datetime.utcnow()
        row.confirmed_type = resolved
        row.confirmed_by_user_id = actor_user_id
        row.confirmed_at = now
        row.status = ClassificationStatus.CONFIRMED.value
        row.requires_review = False
        row.updated_at = now
        self._db.commit()
        self._db.refresh(row)
        self._safe_audit(
            "record_document_classification_confirmed",
            classification_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            predicted_type=row.predicted_type,
            confirmed_type=resolved,
            score=round_score(row.confidence_score),
        )
        self._resolution.maybe_sync_document_type(row, force=False)
        # sync always on confirm
        doc = self._db.get(ElfisDocumentRecord, row.document_id)
        if doc and doc.organization_id == row.organization_id:
            if doc.document_type != resolved:
                doc.document_type = resolved
                self._db.commit()
                self._safe_audit(
                    "record_document_type_effective_updated",
                    classification_id=row.id,
                    document_id=row.document_id,
                    version_id=row.document_version_id,
                    organization_id=row.organization_id,
                    confirmed_type=resolved,
                )
        return row

    def reject(
        self,
        classification_id: str,
        organization_id: int,
        *,
        reason: str | None = None,
        actor_user_id: int | None = None,
        platform: bool = False,
    ) -> ElfisDocumentClassification:
        row = self.get_platform(classification_id) if platform else self.get_for_org(classification_id, organization_id)
        if row.status == ClassificationStatus.REJECTED.value:
            return row
        if row.status == ClassificationStatus.SUPERSEDED.value:
            raise ClassificationValidationError("invalid_status", "Déjà superseded")
        now = datetime.utcnow()
        row.status = ClassificationStatus.REJECTED.value
        row.rejected_at = now
        row.rejection_reason = sanitize_reason(reason)
        row.requires_review = False
        row.updated_at = now
        self._db.commit()
        self._db.refresh(row)
        self._safe_audit(
            "record_document_classification_rejected",
            classification_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
            predicted_type=row.predicted_type,
        )
        return row

    def request_reclassify(
        self,
        classification_id: str,
        organization_id: int,
        *,
        actor_user_id: int | None = None,
        platform: bool = False,
        force: bool = True,
    ):
        row = self.get_platform(classification_id) if platform else self.get_for_org(classification_id, organization_id)
        self._safe_audit(
            "record_document_classification_reclassification_requested",
            classification_id=row.id,
            document_id=row.document_id,
            version_id=row.document_version_id,
            organization_id=row.organization_id,
        )
        pipe = getattr(settings, "document_classification_default_pipeline", None) or PIPELINE_CLASSIFICATION_V1
        job = DocumentProcessingService(self._db, audit_logger=self._audit).create_job(
            organization_id=row.organization_id,
            document_id=row.document_id,
            document_version_id=row.document_version_id,
            pipeline_key=pipe,
            idempotency_key=None if force else f"reclass-{row.document_version_id}-{CLASSIFIER_COMPOSITE_VERSION}",
            metadata={"force_reclassify": True, "from_classification_id": row.id},
            requested_by_user_id=actor_user_id,
        )
        return job

    def _safe_audit(self, method: str, **kwargs: Any) -> None:
        if not self._audit:
            return
        try:
            getattr(self._audit, method)(**{k: v for k, v in kwargs.items() if v is not None})
        except Exception:
            logger.debug("classification_audit_failed", extra={"method": method}, exc_info=True)
