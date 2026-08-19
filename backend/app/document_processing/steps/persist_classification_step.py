"""Étape persist_classification — écrit ElfisDocumentClassification."""

from __future__ import annotations

from app.document_processing.classification.classifiers.base import (
    ClassificationAlternative,
    ClassificationEvidence,
    DocumentClassificationResult,
)
from app.document_processing.classification.service import DocumentClassificationService
from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.types import STEP_PERSIST_CLASSIFICATION


class PersistClassificationStep:
    step_key = STEP_PERSIST_CLASSIFICATION

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        meta = dict(context.job.metadata_json or {})
        pending = meta.get("_classification_pending") or {}
        force = bool(meta.get("force_reclassify"))

        if not pending:
            return ProcessingStepResult(
                success=False,
                status="failed",
                error_code="classification_missing",
                error_message_sanitized="Résultat classification absent",
                retryable=False,
            )

        result = DocumentClassificationResult(
            predicted_type=str(pending.get("predicted_type") or "unknown"),
            confidence_score=float(pending.get("confidence_score") or 0),
            alternatives=[
                ClassificationAlternative(str(a.get("type")), float(a.get("score") or 0))
                for a in (pending.get("alternatives") or [])
                if isinstance(a, dict)
            ],
            evidence=[
                ClassificationEvidence(
                    code=str(e.get("code") or ""),
                    detail=e.get("detail"),
                    weight=float(e.get("weight") or 0),
                )
                for e in (pending.get("evidence") or [])
                if isinstance(e, dict) and e.get("code")
            ],
            requires_review=bool(pending.get("requires_review", True)),
            classifier_key=str(pending.get("classifier_key") or ""),
            classifier_version=str(pending.get("classifier_version") or ""),
        )

        svc = DocumentClassificationService(context.db)
        row = svc.persist_result(
            document=context.document,
            version=context.version,
            result=result,
            job_id=context.job.id,
            force=force,
            source="pipeline",
        )
        # nettoie payload temporaire
        meta.pop("_classification_pending", None)
        context.job.metadata_json = meta
        context.db.flush()

        return ProcessingStepResult(
            success=True,
            status="completed",
            output_summary={
                "classification_id": row.id,
                "predicted_type": row.predicted_type,
                "confidence_score": row.confidence_score,
                "requires_review": row.requires_review,
                "status": row.status,
            },
        )
