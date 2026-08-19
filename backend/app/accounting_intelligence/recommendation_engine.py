"""RecommendationEngine — priorité règles → prefs → historique → similarité → IA."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.journal_resolver import JournalResolver
from app.accounting_engine.rule_engine import RuleEngine
from app.accounting_engine.vat_engine import VATEngine
from app.accounting_intelligence.context_engine import ContextEngine
from app.accounting_intelligence.enums import RecommendationSource
from app.accounting_intelligence.learning_engine import LearningEngine
from app.accounting_intelligence.similarity_engine import SimilarityEngine, SimilarityMatch


@dataclass
class Recommendation:
    account_code: str | None
    vat_account: str | None
    third_party: str | None
    journal_code: str | None
    vat_rate: float | None
    score: float
    primary_source: str
    reason: str
    sources: dict[str, str] = field(default_factory=dict)
    accounts: dict[str, str] = field(default_factory=dict)
    similarity: list[dict[str, Any]] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    ai_hint: dict[str, Any] = field(default_factory=dict)
    confidence_inputs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_code": self.account_code,
            "vat_account": self.vat_account,
            "third_party": self.third_party,
            "journal_code": self.journal_code,
            "vat_rate": self.vat_rate,
            "score": self.score,
            "primary_source": self.primary_source,
            "reason": self.reason,
            "sources": self.sources,
            "accounts": self.accounts,
            "similarity": self.similarity,
            "rules_applied": self.rules_applied,
            "ai_hint": self.ai_hint,
            "confidence_inputs": self.confidence_inputs,
            "disclaimer": "Recommandation uniquement — aucune écriture comptable définitive.",
        }


class RecommendationEngine:
    def __init__(self, db: Session):
        self._db = db
        self._rules = RuleEngine()
        self._context = ContextEngine(db)
        self._learning = LearningEngine(db)
        self._similarity = SimilarityEngine(db)
        self._journals = JournalResolver()
        self._vat = VATEngine()

    def recommend(
        self,
        *,
        organization_id: int,
        payload: dict[str, Any],
        extraction_quality: float | None = None,
        validation_quality: float | None = None,
    ) -> Recommendation:
        rules = self._rules.analyze(payload)
        party = (
            payload.get("supplier_name")
            or (
                payload.get("supplier", {}).get("name")
                if isinstance(payload.get("supplier"), dict)
                else None
            )
            or payload.get("customer_name")
        )
        company = self._context.company_preferences(organization_id=organization_id)
        profile = self._context.profile_dict(organization_id=organization_id)
        history = self._learning.lookup(
            organization_id=organization_id,
            direction=rules.direction,
            document_type=rules.document_type,
            party_name=str(party) if party else None,
        )
        query = {
            **payload,
            "direction": rules.direction,
            "document_type": rules.document_type,
            "party_name": party,
        }
        similar = self._similarity.find_similar(
            organization_id=organization_id, query=query, limit=5
        )
        best_sim: SimilarityMatch | None = similar[0] if similar else None
        sim_accounts = (best_sim.payload.get("accounts") or {}) if best_sim else {}
        sim_journal = (best_sim.payload.get("journal") if best_sim else None)

        # 5. IA — heuristique locale (pas de provider externe) : top compte fréquent du profil
        ai_hint: dict[str, Any] = {}
        freq = profile.get("frequent_accounts") or []
        if freq:
            ai_hint = {
                "expense_or_revenue": freq[0].get("account_code"),
                "reason": "compte_frequent_profil",
                "score": 0.55,
            }

        # Fusion priorité 1→5
        accounts: dict[str, str] = {}
        sources: dict[str, str] = {}

        def _fill(key: str, value: str | None, source: str) -> None:
            if value and key not in accounts:
                accounts[key] = str(value)
                sources[key] = source

        # 1 rules
        for k, v in (rules.account_hints or {}).items():
            _fill(k, v, RecommendationSource.RULES.value)
        # 2 company
        for k, v in company.items():
            _fill(k, v, RecommendationSource.COMPANY.value)
        # 3 history
        for k, v in history.items():
            if k == "journal":
                continue
            _fill(k if k != "revenue_account" else "expense_or_revenue", v, RecommendationSource.HISTORY.value)
        # 4 similarity
        for k, v in sim_accounts.items():
            _fill(k, v, RecommendationSource.SIMILARITY.value)
        # 5 AI
        if ai_hint.get("expense_or_revenue"):
            _fill(
                "expense_or_revenue",
                ai_hint["expense_or_revenue"],
                RecommendationSource.AI.value,
            )

        journal_pref = (
            (rules.account_hints or {}).get("journal")
            or history.get("journal")
            or sim_journal
            or (
                (profile.get("favorite_journals") or [{}])[0].get("journal_code")
                if profile.get("favorite_journals")
                else None
            )
        )
        journal = self._journals.resolve(
            direction=rules.direction,
            document_type=rules.document_type,
            preferred_journal=journal_pref,
        )

        amounts = payload.get("amounts") if isinstance(payload.get("amounts"), dict) else {}
        vat_res = self._vat.compute(
            amount_ht=payload.get("amount_ht") or amounts.get("subtotal_excluding_tax"),
            amount_vat=payload.get("amount_vat")
            or amounts.get("total_tax")
            or payload.get("amount_tva"),
            amount_ttc=payload.get("amount_ttc") or amounts.get("total_including_tax"),
            vat_rate=payload.get("vat_rate") or amounts.get("vat_rate"),
            exempt=rules.exempt_vat,
        )
        # TVA habituelle si absente
        vat_rate_out: float | None = (
            float(vat_res.vat_rate) if vat_res.vat_rate is not None else None
        )
        if vat_rate_out is None and profile.get("habitual_vat_rates"):
            try:
                vat_rate_out = float(profile["habitual_vat_rates"][0]["vat_rate"])
            except (KeyError, TypeError, ValueError, IndexError):
                pass

        primary = RecommendationSource.DEFAULTS.value
        priority_order = [
            RecommendationSource.RULES.value,
            RecommendationSource.COMPANY.value,
            RecommendationSource.HISTORY.value,
            RecommendationSource.SIMILARITY.value,
            RecommendationSource.AI.value,
        ]
        for src in priority_order:
            if src in sources.values():
                primary = src
                break

        score_map = {
            RecommendationSource.RULES.value: 0.92,
            RecommendationSource.COMPANY.value: 0.85,
            RecommendationSource.HISTORY.value: 0.80,
            RecommendationSource.SIMILARITY.value: 0.72,
            RecommendationSource.AI.value: 0.58,
            RecommendationSource.DEFAULTS.value: 0.50,
        }
        base = score_map.get(primary, 0.5)
        if best_sim:
            base = min(1.0, base + 0.08 * best_sim.score)
        if history:
            base = min(1.0, base + 0.05)

        reason_parts = [
            f"source_principale={primary}",
            f"journal={journal.code} ({journal.reason})",
        ]
        if sources.get("expense_or_revenue"):
            reason_parts.append(
                f"compte={accounts.get('expense_or_revenue')} via {sources['expense_or_revenue']}"
            )
        if best_sim:
            reason_parts.append(f"similarite={best_sim.score:.2f}")

        return Recommendation(
            account_code=accounts.get("expense_or_revenue"),
            vat_account=accounts.get("vat_account"),
            third_party=accounts.get("third_party"),
            journal_code=journal.code,
            vat_rate=vat_rate_out,
            score=round(base, 4),
            primary_source=primary,
            reason=" ; ".join(reason_parts),
            sources=sources,
            accounts=accounts,
            similarity=[m.to_dict() for m in similar],
            rules_applied=list(rules.applied or []),
            ai_hint=ai_hint,
            confidence_inputs={
                "extraction_quality": extraction_quality
                or payload.get("extraction_confidence"),
                "validation_quality": validation_quality
                or payload.get("validation_confidence"),
                "history_hit": bool(history),
                "rules_applied": bool(rules.applied),
                "similarity_score": best_sim.score if best_sim else 0.0,
                "learning_score": 0.9 if history else 0.45,
                "ai_score": float(ai_hint.get("score") or 0.4),
            },
        )
