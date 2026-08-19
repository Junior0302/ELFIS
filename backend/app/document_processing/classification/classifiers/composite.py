"""CompositeDocumentClassifier — agrège signaux déterministes."""

from __future__ import annotations

from app.config import settings
from app.document_processing.classification.classifiers.base import (
    ClassificationAlternative,
    ClassificationContext,
    ClassificationEvidence,
    DocumentClassificationResult,
)
from app.document_processing.classification.classifiers.filename import FilenameRuleClassifier
from app.document_processing.classification.classifiers.metadata import MetadataDocumentClassifier
from app.document_processing.classification.classifiers.structural import StructuralFileClassifier
from app.document_processing.classification.scoring import ClassificationScoringPolicy
from app.document_processing.classification.sanitization import round_score
from app.document_processing.classification.types import (
    CLASSIFIER_COMPOSITE_KEY,
    CLASSIFIER_COMPOSITE_VERSION,
    TYPE_INVOICE,
)


class CompositeDocumentClassifier:
    classifier_key = CLASSIFIER_COMPOSITE_KEY
    classifier_version = CLASSIFIER_COMPOSITE_VERSION

    def __init__(self, scoring: ClassificationScoringPolicy | None = None) -> None:
        self._scoring = scoring or ClassificationScoringPolicy.from_settings()
        self._meta = MetadataDocumentClassifier()
        self._filename = FilenameRuleClassifier()
        self._structural = StructuralFileClassifier()

    async def classify(self, context: ClassificationContext) -> DocumentClassificationResult:
        results: list[DocumentClassificationResult] = []
        if getattr(settings, "document_classification_metadata_rules_enabled", True):
            results.append(await self._meta.classify(context))
        if getattr(settings, "document_classification_filename_rules_enabled", True):
            results.append(await self._filename.classify(context))
        results.append(await self._structural.classify(context))

        scores: dict[str, float] = {}
        evidence: list[ClassificationEvidence] = []
        ambiguous = False

        for res in results:
            if res.predicted_type and res.predicted_type != "unknown" and res.confidence_score > 0:
                # poids relatif à la confiance du sous-classifier
                contrib = float(res.confidence_score) * 0.35
                # metadata pèse plus
                if res.classifier_key == "metadata_rules":
                    contrib = float(res.confidence_score) * 0.55
                elif res.classifier_key == "filename_rules":
                    contrib = float(res.confidence_score) * 0.40
                else:
                    contrib = float(res.confidence_score) * 0.15
                scores[res.predicted_type] = scores.get(res.predicted_type, 0.0) + contrib
            for ev in res.evidence:
                evidence.append(ev)
            for alt in res.alternatives:
                if alt.type_key in ("supplier_invoice", "customer_invoice"):
                    ambiguous = True
                scores[alt.type_key] = scores.get(alt.type_key, 0.0) + float(alt.score) * 0.1
            if res.predicted_type == TYPE_INVOICE:
                ambiguous = True

        max_alts = self._scoring.max_alternatives
        if not scores:
            return DocumentClassificationResult(
                predicted_type="unknown",
                confidence_score=0.0,
                evidence=evidence[: int(getattr(settings, "document_classification_evidence_max_items", 20) or 20)],
                requires_review=True,
                classifier_key=self.classifier_key,
                classifier_version=self.classifier_version,
            )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_type, best_raw = ranked[0]
        # normalise vs plafond ~1.2
        conf = round_score(min(1.0, best_raw / 0.85))

        alts = [
            ClassificationAlternative(type_key=k, score=round_score(min(1.0, s / 0.85)))
            for k, s in ranked[1 : max_alts + 1]
            if k != best_type
        ]
        if ambiguous and best_type == TYPE_INVOICE:
            # alternatives directionnelles obligatoires
            existing = {a.type_key for a in alts}
            for t in ("supplier_invoice", "customer_invoice"):
                if t not in existing:
                    alts.insert(0, ClassificationAlternative(t, round_score(conf * 0.5)))
            alts = alts[:max_alts]

        needs_review = self._scoring.requires_review(conf, ambiguous=ambiguous) or conf < self._scoring.confirm_threshold
        if best_type == "unknown" or conf < self._scoring.review_threshold:
            if conf < self._scoring.review_threshold and best_type != TYPE_INVOICE:
                # faible confiance → unknown
                if conf < self._scoring.review_threshold * 0.5:
                    best_type = "unknown"
            needs_review = True

        max_ev = int(getattr(settings, "document_classification_evidence_max_items", 20) or 20)
        return DocumentClassificationResult(
            predicted_type=best_type,
            confidence_score=conf,
            alternatives=alts,
            evidence=evidence[:max_ev],
            requires_review=needs_review,
            classifier_key=self.classifier_key,
            classifier_version=self.classifier_version,
        )
