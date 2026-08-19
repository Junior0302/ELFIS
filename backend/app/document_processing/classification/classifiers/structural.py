"""StructuralFileClassifier — conteneur MIME uniquement, aucun texte."""

from __future__ import annotations

from app.document_processing.classification.classifiers.base import (
    ClassificationContext,
    ClassificationEvidence,
    DocumentClassificationResult,
)
from app.document_processing.classification.scoring import WEIGHT_MIME_STRUCTURE, WEIGHT_WEAK_MIME_ONLY


class StructuralFileClassifier:
    classifier_key = "structural_file"
    classifier_version = "1.0.0"

    async def classify(self, context: ClassificationContext) -> DocumentClassificationResult:
        obj = context.storage_object
        mime = ""
        if obj is not None:
            mime = (obj.mime_type_detected or obj.mime_type_declared or "").lower()
        if not mime:
            mime = (context.version.mime_type or "").lower()

        evidence: list[ClassificationEvidence] = []
        predicted = "unknown"
        score = 0.0

        if mime.startswith("application/pdf") or mime == "application/pdf":
            evidence.append(
                ClassificationEvidence(code="structure:pdf", detail="pdf", weight=WEIGHT_MIME_STRUCTURE)
            )
            # PDF seul → supporting faible, pas de type métier
            predicted = "supporting_document"
            score = WEIGHT_WEAK_MIME_ONLY
        elif mime.startswith("image/"):
            evidence.append(
                ClassificationEvidence(code="structure:image", detail=mime.split("/")[-1][:16], weight=WEIGHT_MIME_STRUCTURE)
            )
            predicted = "receipt"
            score = WEIGHT_WEAK_MIME_ONLY * 1.2
        elif "spreadsheet" in mime or mime in (
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv",
        ):
            evidence.append(
                ClassificationEvidence(code="structure:spreadsheet", weight=WEIGHT_MIME_STRUCTURE)
            )
            predicted = "bank_statement"
            score = WEIGHT_MIME_STRUCTURE * 0.6
        elif "wordprocessingml" in mime or "msword" in mime:
            evidence.append(
                ClassificationEvidence(code="structure:docx", weight=WEIGHT_MIME_STRUCTURE)
            )
            predicted = "contract"
            score = WEIGHT_WEAK_MIME_ONLY
        else:
            if mime:
                evidence.append(ClassificationEvidence(code="structure:other", detail=mime[:40], weight=0.0))

        return DocumentClassificationResult(
            predicted_type=predicted,
            confidence_score=min(1.0, score / 0.25) if score else 0.0,
            evidence=evidence,
            requires_review=True,
            classifier_key=self.classifier_key,
            classifier_version=self.classifier_version,
        )
