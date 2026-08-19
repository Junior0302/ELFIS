"""Scoring heuristique explicable — pas une probabilité statistique."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class ClassificationScoringPolicy:
    confirm_threshold: float = 0.90
    review_threshold: float = 0.55
    auto_confirm: bool = False
    max_alternatives: int = 3

    @classmethod
    def from_settings(cls) -> ClassificationScoringPolicy:
        confirm = float(getattr(settings, "document_classification_confirm_threshold", 0.90) or 0.90)
        review = float(getattr(settings, "document_classification_review_threshold", 0.55) or 0.55)
        confirm = max(0.0, min(1.0, confirm))
        review = max(0.0, min(confirm, review))
        return cls(
            confirm_threshold=confirm,
            review_threshold=review,
            auto_confirm=bool(getattr(settings, "document_classification_auto_confirm", False)),
            max_alternatives=int(getattr(settings, "document_classification_max_alternatives", 3) or 3),
        )

    def requires_review(self, score: float, *, ambiguous: bool = False) -> bool:
        if ambiguous:
            return True
        if score < self.confirm_threshold:
            return True
        return False

    def is_auto_confirmable(self, score: float, *, ambiguous: bool = False) -> bool:
        if not self.auto_confirm or ambiguous:
            return False
        return score >= self.confirm_threshold


# Poids relatifs (somme non normalisée a priori — composite normalise)
WEIGHT_DECLARED_TYPE = 0.45
WEIGHT_ENTITY_LINK = 0.40
WEIGHT_PRODUCT_SOURCE = 0.25
WEIGHT_FILENAME_KEYWORD = 0.22
WEIGHT_MIME_STRUCTURE = 0.08
WEIGHT_WEAK_MIME_ONLY = 0.05
