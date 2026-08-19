"""FilenameRuleClassifier — mots-clés normalisés, pas de filename stocké."""

from __future__ import annotations

import re
import unicodedata

from app.config import settings
from app.document_processing.classification.classifiers.base import (
    ClassificationAlternative,
    ClassificationContext,
    ClassificationEvidence,
    DocumentClassificationResult,
)
from app.document_processing.classification.scoring import WEIGHT_FILENAME_KEYWORD
from app.document_processing.classification.types import TYPE_INVOICE

# (mot-clé normalisé, type, direction_fiable)
_RULES: tuple[tuple[str, str, bool], ...] = (
    ("avoir", "credit_note", True),
    ("credit-note", "credit_note", True),
    ("creditnote", "credit_note", True),
    ("credit_note", "credit_note", True),
    ("devis", "quote", True),
    ("quote", "quote", True),
    ("quotation", "quote", True),
    ("releve", "bank_statement", True),
    ("relevé", "bank_statement", True),
    ("statement", "bank_statement", True),
    ("contrat", "contract", True),
    ("contract", "contract", True),
    ("bulletin", "payroll_document", True),
    ("payslip", "payroll_document", True),
    ("paie", "payroll_document", True),
    ("bon-commande", "purchase_order", True),
    ("bon_commande", "purchase_order", True),
    ("purchase-order", "purchase_order", True),
    ("livraison", "delivery_note", True),
    ("delivery", "delivery_note", True),
    ("note-frais", "expense_report", True),
    ("expense", "expense_report", True),
    ("facture-fournisseur", "supplier_invoice", True),
    ("facture_fournisseur", "supplier_invoice", True),
    ("supplier-invoice", "supplier_invoice", True),
    ("facture-client", "customer_invoice", True),
    ("facture_client", "customer_invoice", True),
    ("customer-invoice", "customer_invoice", True),
    ("facture", TYPE_INVOICE, False),
    ("invoice", TYPE_INVOICE, False),
)


def _normalize_filename(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    # retire emails / digits longs
    text = re.sub(r"[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+", " ", text)
    text = re.sub(r"[^a-z0-9._-]+", " ", text)
    return text.strip()


class FilenameRuleClassifier:
    classifier_key = "filename_rules"
    classifier_version = "1.0.0"

    async def classify(self, context: ClassificationContext) -> DocumentClassificationResult:
        if not getattr(settings, "document_classification_filename_rules_enabled", True):
            return DocumentClassificationResult(
                predicted_type="unknown",
                confidence_score=0.0,
                requires_review=True,
                classifier_key=self.classifier_key,
                classifier_version=self.classifier_version,
            )

        raw = context.version.original_filename or ""
        # extension seule pour preuve structurelle — pas le nom
        ext = ""
        if "." in raw:
            ext = raw.rsplit(".", 1)[-1].lower()[:12]

        normalized = _normalize_filename(raw)
        scores: dict[str, float] = {}
        evidence: list[ClassificationEvidence] = []
        ambiguous = False

        for keyword, type_key, reliable in _RULES:
            token = keyword.replace("é", "e")
            hay = normalized.replace("é", "e")
            if token in hay or keyword in normalized:
                w = WEIGHT_FILENAME_KEYWORD if reliable else WEIGHT_FILENAME_KEYWORD * 0.75
                scores[type_key] = scores.get(type_key, 0.0) + w
                evidence.append(
                    ClassificationEvidence(
                        code=f"keyword_match:{keyword.split('-')[0][:24]}",
                        detail=type_key,
                        weight=w,
                    )
                )
                if not reliable:
                    ambiguous = True
                # un seul match prioritaire par règle la plus spécifique d'abord
                break

        if not scores:
            if ext:
                evidence.append(ClassificationEvidence(code=f"extension:{ext}", weight=0.0))
            return DocumentClassificationResult(
                predicted_type="unknown",
                confidence_score=0.0,
                evidence=evidence,
                requires_review=True,
                classifier_key=self.classifier_key,
                classifier_version=self.classifier_version,
            )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_type, best = ranked[0]
        conf = min(1.0, best / 0.35)
        alts: list[ClassificationAlternative] = []
        if ambiguous and best_type == TYPE_INVOICE:
            alts = [
                ClassificationAlternative("supplier_invoice", conf * 0.45),
                ClassificationAlternative("customer_invoice", conf * 0.45),
            ]

        return DocumentClassificationResult(
            predicted_type=best_type,
            confidence_score=conf,
            alternatives=alts,
            evidence=evidence,
            requires_review=True,
            classifier_key=self.classifier_key,
            classifier_version=self.classifier_version,
        )
