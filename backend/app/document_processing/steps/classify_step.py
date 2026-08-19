"""Étape classify_document — produit un résultat en mémoire (résumé step)."""

from __future__ import annotations

from app.document_processing.classification.service import DocumentClassificationService
from app.document_processing.context import ProcessingContext, ProcessingStepResult
from app.document_processing.types import STEP_CLASSIFY


class ClassifyDocumentStep:
    step_key = STEP_CLASSIFY

    async def execute(self, context: ProcessingContext) -> ProcessingStepResult:
        svc = DocumentClassificationService(context.db)
        result = await svc.run_classifier(
            document=context.document,
            version=context.version,
            storage_object=context.storage_object,
            job_id=context.job.id,
        )
        # stocke un résumé borné dans le step output ; persist se fait à l'étape suivante
        # via metadata job (orchestrateur lit output) — on utilise output_summary + job metadata
        summary = {
            "predicted_type": result.predicted_type,
            "confidence_score": result.confidence_score,
            "requires_review": result.requires_review,
            "classifier_key": result.classifier_key,
            "classifier_version": result.classifier_version,
            "alternatives": [{"type": a.type_key, "score": a.score} for a in result.alternatives[:3]],
            "evidence_codes": [e.code for e in result.evidence[:20]],
        }
        # attache le résultat complet sur le job metadata temporaire pour persist
        meta = dict(context.job.metadata_json or {})
        meta["_classification_pending"] = {
            **summary,
            "evidence": [{"code": e.code, "detail": e.detail, "weight": e.weight} for e in result.evidence[:20]],
        }
        context.job.metadata_json = meta
        context.db.flush()
        return ProcessingStepResult(success=True, status="completed", output_summary=summary)
