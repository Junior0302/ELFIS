"""ConfidenceEngine — score global de la proposition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfidenceResult:
    score: float
    detail: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "detail": self.detail, "reasons": self.reasons}


class ConfidenceEngine:
    """
    Score 0–1 basé sur :
    extraction, validation, cohérence, historique, similarité, apprentissage, score IA.
    """

    def score(
        self,
        *,
        extraction_quality: float | None = None,
        validation_quality: float | None = None,
        history_hit: bool = False,
        rules_applied: bool = False,
        consistency_ok: bool = False,
        warning_count: int = 0,
        error_count: int = 0,
        similarity_score: float | None = None,
        learning_score: float | None = None,
        ai_score: float | None = None,
    ) -> ConfidenceResult:
        detail: dict[str, float] = {}
        reasons: list[str] = []

        eq = 0.7 if extraction_quality is None else max(0.0, min(1.0, float(extraction_quality)))
        vq = 0.75 if validation_quality is None else max(0.0, min(1.0, float(validation_quality)))
        detail["extraction"] = eq
        detail["validation"] = vq

        hist = 0.9 if history_hit else 0.5
        if learning_score is not None:
            hist = max(0.0, min(1.0, float(learning_score)))
        detail["history"] = hist
        detail["learning"] = hist
        if history_hit or (learning_score is not None and learning_score >= 0.7):
            reasons.append("historique_fournisseur")

        rules = 0.85 if rules_applied else 0.55
        detail["rules"] = rules
        if rules_applied:
            reasons.append("regles_metier")

        cons = 0.95 if consistency_ok else 0.35
        detail["consistency"] = cons
        if consistency_ok:
            reasons.append("equilibre_ok")
        else:
            reasons.append("equilibre_ko")

        sim = 0.5 if similarity_score is None else max(0.0, min(1.0, float(similarity_score)))
        detail["similarity"] = sim
        if sim >= 0.7:
            reasons.append("similarite_forte")

        ai = 0.4 if ai_score is None else max(0.0, min(1.0, float(ai_score)))
        detail["ai"] = ai
        if ai >= 0.6:
            reasons.append("suggestion_ia")

        base = (
            0.18 * eq
            + 0.18 * vq
            + 0.14 * cons
            + 0.12 * hist
            + 0.12 * rules
            + 0.14 * sim
            + 0.06 * hist  # learning (même axe, poids séparé dans détail)
            + 0.06 * ai
        )
        # Normalisation légère : poids sum = 1.0
        penalty = min(0.35, 0.04 * warning_count + 0.12 * error_count)
        score = max(0.0, min(1.0, round(base - penalty, 4)))
        if penalty:
            reasons.append(f"penalite_{penalty:.2f}")
        return ConfidenceResult(score=score, detail=detail, reasons=reasons)
