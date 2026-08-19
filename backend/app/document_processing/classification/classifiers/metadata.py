"""MetadataDocumentClassifier — MIME, source, product, type déclaré, liens."""

from __future__ import annotations

from app.document_processing.classification.classifiers.base import (
    ClassificationAlternative,
    ClassificationContext,
    ClassificationEvidence,
    DocumentClassificationResult,
)
from app.document_processing.classification.scoring import (
    WEIGHT_DECLARED_TYPE,
    WEIGHT_ENTITY_LINK,
    WEIGHT_PRODUCT_SOURCE,
)
from app.document_processing.classification.taxonomy import get_document_type_registry
from app.document_processing.classification.types import TYPE_INVOICE


class MetadataDocumentClassifier:
    classifier_key = "metadata_rules"
    classifier_version = "1.0.0"

    async def classify(self, context: ClassificationContext) -> DocumentClassificationResult:
        registry = get_document_type_registry()
        scores: dict[str, float] = {}
        evidence: list[ClassificationEvidence] = []
        ambiguous = False

        declared = (context.document.document_type or "").strip()
        if declared and declared not in ("file", "unknown", ""):
            resolved = registry.resolve_key(declared)
            if resolved and resolved != "unknown":
                scores[resolved] = scores.get(resolved, 0.0) + WEIGHT_DECLARED_TYPE
                evidence.append(
                    ClassificationEvidence(
                        code="declared_type_match",
                        detail=resolved,
                        weight=WEIGHT_DECLARED_TYPE,
                    )
                )
            elif declared.lower() in ("invoice", "facture"):
                scores[TYPE_INVOICE] = scores.get(TYPE_INVOICE, 0.0) + WEIGHT_DECLARED_TYPE * 0.7
                ambiguous = True
                evidence.append(
                    ClassificationEvidence(
                        code="declared_type_ambiguous_invoice",
                        detail="invoice",
                        weight=WEIGHT_DECLARED_TYPE * 0.7,
                    )
                )

        for link in context.links:
            et = (link.entity_type or "").lower()
            if et in ("supplier_invoice", "purchase_invoice", "vendor_invoice"):
                scores["supplier_invoice"] = scores.get("supplier_invoice", 0.0) + WEIGHT_ENTITY_LINK
                evidence.append(
                    ClassificationEvidence(code="entity_link", detail="supplier_invoice", weight=WEIGHT_ENTITY_LINK)
                )
            elif et in ("customer_invoice", "sales_invoice", "invoice") and link.relation_type in (
                "source",
                "attachment",
            ):
                # entity_type=invoice sans direction → générique + revue
                if et == "invoice":
                    scores[TYPE_INVOICE] = scores.get(TYPE_INVOICE, 0.0) + WEIGHT_ENTITY_LINK * 0.8
                    ambiguous = True
                    evidence.append(
                        ClassificationEvidence(code="entity_link_ambiguous", detail="invoice", weight=WEIGHT_ENTITY_LINK * 0.8)
                    )
                else:
                    scores["customer_invoice"] = scores.get("customer_invoice", 0.0) + WEIGHT_ENTITY_LINK
                    evidence.append(
                        ClassificationEvidence(
                            code="entity_link", detail="customer_invoice", weight=WEIGHT_ENTITY_LINK
                        )
                    )
            elif et in ("quote", "devis"):
                scores["quote"] = scores.get("quote", 0.0) + WEIGHT_ENTITY_LINK
                evidence.append(
                    ClassificationEvidence(code="entity_link", detail="quote", weight=WEIGHT_ENTITY_LINK)
                )

        product = (context.document.product or "").lower()
        source = (context.version.source or context.document.source or "").lower()
        if product in ("comptapilot", "elfis-core") and source in ("upload", "manual_upload", "api"):
            scores["supporting_document"] = scores.get("supporting_document", 0.0) + WEIGHT_PRODUCT_SOURCE * 0.3
            evidence.append(
                ClassificationEvidence(
                    code="source_signal",
                    detail="manual_upload",
                    weight=WEIGHT_PRODUCT_SOURCE * 0.3,
                )
            )

        if not scores:
            return DocumentClassificationResult(
                predicted_type="unknown",
                confidence_score=0.0,
                evidence=evidence,
                requires_review=True,
                classifier_key=self.classifier_key,
                classifier_version=self.classifier_version,
            )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_type, best_score = ranked[0]
        # normalise grossièrement vs poids max plausible ~1.1
        conf = min(1.0, best_score / 0.9)
        alts = [
            ClassificationAlternative(type_key=k, score=min(1.0, s / 0.9))
            for k, s in ranked[1:4]
        ]
        if ambiguous and best_type == TYPE_INVOICE:
            alts = [
                ClassificationAlternative(type_key="supplier_invoice", score=conf * 0.5),
                ClassificationAlternative(type_key="customer_invoice", score=conf * 0.5),
            ] + alts

        return DocumentClassificationResult(
            predicted_type=best_type,
            confidence_score=conf,
            alternatives=alts,
            evidence=evidence,
            requires_review=True,
            classifier_key=self.classifier_key,
            classifier_version=self.classifier_version,
        )
