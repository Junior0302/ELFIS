"""IntelligenceService — orchestration recommandations / feedback / retrain."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.confidence_engine import ConfidenceEngine
from app.accounting_engine.models import ElfisAccountingEngineProposal
from app.accounting_engine.proposal_service import ProposalService
from app.accounting_intelligence.audit import write_intelligence_audit
from app.accounting_intelligence.context_engine import ContextEngine
from app.accounting_intelligence.enums import FeedbackAction
from app.accounting_intelligence.events import publish_intelligence_event
from app.accounting_intelligence.exceptions import IntelligenceNotFoundError
from app.accounting_intelligence.explanation_engine import ExplanationEngine
from app.accounting_intelligence.feedback import FeedbackEngine
from app.accounting_intelligence.learning_engine import LearningEngine
from app.accounting_intelligence.models import ElfisAiRecommendationHistory
from app.accounting_intelligence.recommendation_engine import RecommendationEngine
from app.accounting_intelligence.rule_optimizer import RuleOptimizer
from app.accounting_intelligence.similarity_engine import SimilarityEngine


class IntelligenceService:
    def __init__(self, db: Session):
        self._db = db
        self._reco = RecommendationEngine(db)
        self._explain = ExplanationEngine()
        self._feedback = FeedbackEngine(db)
        self._learning = LearningEngine(db)
        self._context = ContextEngine(db)
        self._similarity = SimilarityEngine(db)
        self._optimizer = RuleOptimizer(db)
        self._confidence = ConfidenceEngine()
        self._proposals = ProposalService(db)

    def recommend(
        self,
        *,
        organization_id: int,
        actor_user_id: int | None,
        payload: dict[str, Any] | None = None,
        proposal_id: str | None = None,
        generate_proposal: bool = False,
    ) -> dict[str, Any]:
        snap = dict(payload or {})
        prop: ElfisAccountingEngineProposal | None = None
        if proposal_id:
            prop = (
                self._db.query(ElfisAccountingEngineProposal)
                .filter(ElfisAccountingEngineProposal.organization_id == organization_id)
                .filter(ElfisAccountingEngineProposal.id == proposal_id)
                .first()
            )
            if not prop:
                raise IntelligenceNotFoundError("proposition introuvable")
            snap = {**(prop.input_snapshot_json or {}), **snap}

        reco = self._reco.recommend(organization_id=organization_id, payload=snap)
        conf = self._confidence.score(
            extraction_quality=reco.confidence_inputs.get("extraction_quality"),
            validation_quality=reco.confidence_inputs.get("validation_quality"),
            history_hit=bool(reco.confidence_inputs.get("history_hit")),
            rules_applied=bool(reco.confidence_inputs.get("rules_applied")),
            consistency_ok=True,
            similarity_score=float(reco.confidence_inputs.get("similarity_score") or 0),
            learning_score=float(reco.confidence_inputs.get("learning_score") or 0.45),
            ai_score=float(reco.confidence_inputs.get("ai_score") or 0.4),
        )
        explanation = self._explain.explain(
            recommendation=reco, confidence=conf.to_dict()
        )

        linked_proposal_id = proposal_id
        comparison = None
        if generate_proposal and not proposal_id:
            # Enrichir payload avec hints recommandés puis générer proposition foundation
            enriched = dict(snap)
            if reco.accounts:
                enriched["intelligence_account_hints"] = reco.accounts
            if reco.journal_code:
                enriched["preferred_journal"] = reco.journal_code
            row = self._proposals.generate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                payload=enriched,
                source_document_id=snap.get("source_document_id")
                or snap.get("document_number"),
                source_kind="intelligence",
            )
            linked_proposal_id = row.id
            comparison = {
                "before": None,
                "after": {
                    "journal_code": row.journal_code,
                    "lines": row.lines_json,
                    "confidence_score": row.confidence_score,
                },
            }

        hist = ElfisAiRecommendationHistory(
            organization_id=organization_id,
            proposal_id=linked_proposal_id,
            direction=snap.get("direction") or reco.primary_source,
            document_type=snap.get("document_type"),
            party_name=snap.get("supplier_name") or snap.get("customer_name"),
            account_code=reco.account_code,
            journal_code=reco.journal_code,
            vat_rate=reco.vat_rate,
            score=reco.score,
            primary_source=reco.primary_source,
            reason=reco.reason,
            recommendation_json=reco.to_dict(),
            explanation_json=explanation,
            confidence_detail_json=conf.to_dict(),
            input_snapshot_json=snap,
            actor_user_id=actor_user_id,
        )
        # Fix direction from rules via reco confidence - use payload
        from app.accounting_engine.rule_engine import RuleEngine

        rules = RuleEngine().analyze(snap)
        hist.direction = rules.direction
        hist.document_type = rules.document_type
        self._db.add(hist)
        self._db.flush()

        write_intelligence_audit(
            self._db,
            organization_id=organization_id,
            action="recommendation.generated",
            entity_type="recommendation",
            entity_id=hist.id,
            actor_user_id=actor_user_id,
            detail={"score": reco.score, "source": reco.primary_source},
        )
        write_intelligence_audit(
            self._db,
            organization_id=organization_id,
            action="explanation",
            entity_type="recommendation",
            entity_id=hist.id,
            actor_user_id=actor_user_id,
            detail={"narrative": explanation.get("narrative")},
        )
        publish_intelligence_event(
            self._db,
            event_type="recommendation.generated",
            organization_id=organization_id,
            aggregate_id=hist.id,
            actor_user_id=actor_user_id,
            payload={"score": reco.score, "proposal_id": linked_proposal_id},
        )
        self._db.commit()

        return {
            "recommendation_id": hist.id,
            "proposal_id": linked_proposal_id,
            "recommendation": reco.to_dict(),
            "explanation": explanation,
            "confidence": conf.to_dict(),
            "context": self._context.profile_dict(organization_id=organization_id),
            "comparison": comparison,
            "disclaimer": "Recommandation uniquement — aucune écriture comptable définitive.",
        }

    def get_recommendation(
        self, *, organization_id: int, recommendation_id: str
    ) -> dict[str, Any]:
        row = (
            self._db.query(ElfisAiRecommendationHistory)
            .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
            .filter(ElfisAiRecommendationHistory.id == recommendation_id)
            .first()
        )
        if not row:
            raise IntelligenceNotFoundError("recommandation introuvable")
        return self._hist_dict(row)

    def list_recommendations(
        self, *, organization_id: int, limit: int = 20
    ) -> list[dict[str, Any]]:
        rows = (
            self._db.query(ElfisAiRecommendationHistory)
            .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
            .order_by(ElfisAiRecommendationHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._hist_dict(r) for r in rows]

    def explanations(
        self,
        *,
        organization_id: int,
        recommendation_id: str | None = None,
        proposal_id: str | None = None,
    ) -> dict[str, Any]:
        if recommendation_id:
            row = (
                self._db.query(ElfisAiRecommendationHistory)
                .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
                .filter(ElfisAiRecommendationHistory.id == recommendation_id)
                .first()
            )
            if not row:
                raise IntelligenceNotFoundError("recommandation introuvable")
            write_intelligence_audit(
                self._db,
                organization_id=organization_id,
                action="explanation.read",
                entity_type="recommendation",
                entity_id=row.id,
                detail={},
            )
            self._db.commit()
            return {
                "recommendation_id": row.id,
                "explanation": row.explanation_json or {},
                "recommendation": row.recommendation_json or {},
                "confidence": row.confidence_detail_json or {},
            }
        if proposal_id:
            # Générer explication à la volée depuis proposition
            prop = self._proposals.get_proposal(
                organization_id=organization_id, proposal_id=proposal_id
            )
            reco = self._reco.recommend(
                organization_id=organization_id,
                payload=prop.input_snapshot_json or {},
            )
            conf = {
                "score": prop.confidence_score,
                "detail": (prop.confidence_detail_json or {}).get("detail")
                or prop.confidence_detail_json
                or {},
            }
            return {
                "proposal_id": proposal_id,
                "explanation": self._explain.explain(recommendation=reco, confidence=conf),
                "foundation_explanations": prop.explanations_json or [],
            }
        raise IntelligenceNotFoundError("recommendation_id ou proposal_id requis")

    def learning_state(self, *, organization_id: int) -> dict[str, Any]:
        return {
            "items": self._learning.list_learned(organization_id=organization_id),
            "context": self._context.profile_dict(organization_id=organization_id),
        }

    def submit_feedback(
        self,
        *,
        organization_id: int,
        actor_user_id: int | None,
        action: str,
        recommendation_id: str | None = None,
        proposal_id: str | None = None,
        validation_seconds: float | None = None,
        comment: str | None = None,
        modifications: dict[str, Any] | None = None,
        cancelled: bool = False,
        import_rejected: bool = False,
    ) -> dict[str, Any]:
        fb, gate = self._feedback.record(
            organization_id=organization_id,
            action=action,
            actor_user_id=actor_user_id,
            recommendation_id=recommendation_id,
            proposal_id=proposal_id,
            validation_seconds=validation_seconds,
            comment=comment,
            modifications=modifications,
            cancelled=cancelled,
            import_rejected=import_rejected,
        )
        write_intelligence_audit(
            self._db,
            organization_id=organization_id,
            action="feedback",
            entity_type="feedback",
            entity_id=fb.id,
            actor_user_id=actor_user_id,
            detail={"action": action, "learned": fb.learned, "gate": gate.value},
        )
        if fb.learned:
            write_intelligence_audit(
                self._db,
                organization_id=organization_id,
                action="learning.created",
                entity_type="feedback",
                entity_id=fb.id,
                actor_user_id=actor_user_id,
                detail={},
            )
            publish_intelligence_event(
                self._db,
                event_type="learning.created",
                organization_id=organization_id,
                aggregate_id=fb.id,
                actor_user_id=actor_user_id,
                payload={"feedback_id": fb.id},
            )

        event_map = {
            FeedbackAction.ACCEPT.value: "recommendation.accepted",
            FeedbackAction.MODIFY.value: "recommendation.modified",
            FeedbackAction.REJECT.value: "recommendation.rejected",
        }
        publish_intelligence_event(
            self._db,
            event_type="feedback.received",
            organization_id=organization_id,
            aggregate_id=fb.id,
            actor_user_id=actor_user_id,
            payload={"action": action, "learn_gate": gate.value},
        )
        if action in event_map:
            publish_intelligence_event(
                self._db,
                event_type=event_map[action],
                organization_id=organization_id,
                aggregate_id=recommendation_id or fb.id,
                actor_user_id=actor_user_id,
                payload={"feedback_id": fb.id},
            )
        self._db.commit()
        return {
            "feedback_id": fb.id,
            "action": fb.action,
            "learned": fb.learned,
            "learn_gate": gate.value,
            "validation_seconds": fb.validation_seconds,
            "comment": fb.comment,
        }

    def retrain(self, *, organization_id: int, actor_user_id: int | None) -> dict[str, Any]:
        profile = self._context.rebuild(organization_id=organization_id)
        optimizations = self._optimizer.analyze(organization_id=organization_id)
        write_intelligence_audit(
            self._db,
            organization_id=organization_id,
            action="optimization",
            entity_type="context_profile",
            entity_id=profile.id,
            actor_user_id=actor_user_id,
            detail={
                "version": profile.version,
                "optimizations_count": len(optimizations.get("optimizations") or []),
            },
        )
        self._db.commit()
        return {
            "context": self._context.profile_dict(organization_id=organization_id),
            "optimizations": optimizations,
            "auto_rules_modified": False,
        }

    def similarity(
        self,
        *,
        organization_id: int,
        payload: dict[str, Any],
        limit: int = 5,
    ) -> dict[str, Any]:
        matches = self._similarity.find_similar(
            organization_id=organization_id, query=payload, limit=limit
        )
        self._db.commit()
        return {
            "matches": [m.to_dict() for m in matches],
            "count": len(matches),
        }

    @staticmethod
    def _hist_dict(row: ElfisAiRecommendationHistory) -> dict[str, Any]:
        return {
            "id": row.id,
            "proposal_id": row.proposal_id,
            "direction": row.direction,
            "document_type": row.document_type,
            "party_name": row.party_name,
            "account_code": row.account_code,
            "journal_code": row.journal_code,
            "vat_rate": row.vat_rate,
            "score": row.score,
            "primary_source": row.primary_source,
            "reason": row.reason,
            "recommendation": row.recommendation_json or {},
            "explanation": row.explanation_json or {},
            "confidence": row.confidence_detail_json or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "disclaimer": "Recommandation uniquement — aucune écriture comptable définitive.",
        }
