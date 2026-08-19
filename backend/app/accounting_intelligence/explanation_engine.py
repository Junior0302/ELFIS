"""ExplanationEngine — explications humaines lisibles."""

from __future__ import annotations

from typing import Any

from app.accounting_intelligence.recommendation_engine import Recommendation


class ExplanationEngine:
    SOURCE_FR = {
        "rules": "règles comptables",
        "company": "préférences de l'entreprise",
        "history": "historique de validations",
        "similarity": "documents similaires",
        "ai": "suggestion du profil IA local",
        "defaults": "valeurs par défaut du plan comptable",
    }

    def explain(
        self,
        *,
        recommendation: Recommendation,
        confidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conf = confidence or {}
        detail = conf.get("detail") or conf.get("confidence_detail") or {}
        score = conf.get("score", recommendation.score)

        why_account = self._why_account(recommendation)
        why_vat = self._why_vat(recommendation)
        why_journal = self._why_journal(recommendation)
        why_score = self._why_score(recommendation)
        why_confidence = self._why_confidence(score, detail, recommendation)

        narrative = (
            f"{why_account} {why_vat} {why_journal} "
            f"Score de recommandation : {recommendation.score:.0%}. "
            f"{why_confidence}"
        )

        return {
            "why_account": why_account,
            "why_vat": why_vat,
            "why_journal": why_journal,
            "why_score": why_score,
            "why_confidence": why_confidence,
            "narrative": narrative.strip(),
            "primary_source": recommendation.primary_source,
            "sources": recommendation.sources,
            "similarity_summary": [
                {
                    "score": s.get("score"),
                    "party": (s.get("payload") or {}).get("party_name")
                    or (s.get("payload") or {}).get("supplier_name"),
                }
                for s in (recommendation.similarity or [])[:3]
            ],
            "human_readable": True,
        }

    def _label(self, source: str | None) -> str:
        return self.SOURCE_FR.get(source or "", source or "inconnu")

    def _why_account(self, rec: Recommendation) -> str:
        code = rec.account_code or "non déterminé"
        src = self._label(rec.sources.get("expense_or_revenue") or rec.primary_source)
        return f"Le compte {code} a été choisi d'après {src}."

    def _why_vat(self, rec: Recommendation) -> str:
        if rec.vat_rate is None:
            return "Aucun taux de TVA n'a pu être déterminé avec certitude."
        vat_acc = rec.vat_account or "—"
        return (
            f"La TVA retenue est de {rec.vat_rate:g} % "
            f"(compte {vat_acc}), cohérente avec le document et le contexte entreprise."
        )

    def _why_journal(self, rec: Recommendation) -> str:
        j = rec.journal_code or "—"
        return f"Le journal {j} correspond au type de flux détecté (achats, ventes, banque, caisse ou OD)."

    def _why_score(self, rec: Recommendation) -> str:
        return (
            f"Le score {rec.score:.0%} reflète la source principale "
            f"« {self._label(rec.primary_source)} » et la similarité éventuelle."
        )

    def _why_confidence(
        self, score: Any, detail: dict[str, Any], rec: Recommendation
    ) -> str:
        parts = []
        if detail.get("extraction") is not None:
            parts.append(f"extraction {float(detail['extraction']):.0%}")
        if detail.get("validation") is not None:
            parts.append(f"validation {float(detail['validation']):.0%}")
        if detail.get("similarity") is not None:
            parts.append(f"similarité {float(detail['similarity']):.0%}")
        if detail.get("learning") is not None:
            parts.append(f"apprentissage {float(detail['learning']):.0%}")
        if detail.get("consistency") is not None:
            parts.append(f"cohérence {float(detail['consistency']):.0%}")
        joined = ", ".join(parts) if parts else rec.reason
        try:
            s = float(score)
            return f"La confiance globale ({s:.0%}) combine : {joined}."
        except (TypeError, ValueError):
            return f"La confiance combine : {joined}."
