"""Règles déterministes V1 — factory de décisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.decision_center.enums import (
    DecisionActionType,
    DecisionSeverity,
    DecisionSourceType,
    DecisionType,
)


@dataclass(frozen=True)
class DecisionDraft:
    decision_type: str
    source_type: str
    source_id: str
    severity: str
    title: str
    summary: str
    explanation: str
    recommended_action_type: str
    recommended_action_path: str | None
    required_permission: str | None
    created_by_rule: str
    rule_version: str
    deduplication_key: str
    confidence: float | None = None
    metadata: dict[str, Any] | None = None
    source_event_id: str | None = None
    still_active: bool = True


class AccountingProposalRequiresReviewRule:
    rule_id = "accounting_proposal_requires_review"
    version = "1"
    source_type = DecisionSourceType.ACCOUNTING_PROPOSAL

    def evaluate(self, proposal: Any, *, source_event_id: str | None = None) -> DecisionDraft | None:
        status = getattr(proposal, "status", "") or ""
        requires = bool(getattr(proposal, "requires_review", False))
        active = requires or status == "requires_review"
        if status in {"validated", "rejected", "cancelled"}:
            active = False
        if not active and status != "requires_review" and not requires:
            # Draft de résolution uniquement si on avait une clé connue
            return None
        if not active:
            return None

        proposal_id = str(getattr(proposal, "proposal_id", "") or getattr(proposal, "id", ""))
        reasons = getattr(proposal, "review_reasons", None) or []
        reason_txt = ", ".join(str(r) for r in reasons[:3]) if isinstance(reasons, list) and reasons else (
            "Des contrôles métier ont demandé une vérification humaine."
        )
        return DecisionDraft(
            decision_type=DecisionType.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
            source_type=DecisionSourceType.ACCOUNTING_PROPOSAL,
            source_id=proposal_id,
            severity=DecisionSeverity.HIGH,
            title="Cette proposition comptable nécessite une vérification",
            summary="Une revue humaine est recommandée avant validation.",
            explanation=str(reason_txt),
            recommended_action_type=DecisionActionType.REVIEW,
            recommended_action_path=f"/accounting/proposals/{proposal_id}",
            required_permission="ai.analysis",
            created_by_rule=self.rule_id,
            rule_version=self.version,
            deduplication_key=f"{DecisionType.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW}:{proposal_id}:v{self.version}",
            source_event_id=source_event_id,
            metadata={"status": status},
            still_active=True,
        )

    def is_resolved(self, proposal: Any) -> bool:
        status = getattr(proposal, "status", "") or ""
        if status in {"validated", "rejected", "cancelled"}:
            return True
        if status == "ready_for_validation" and not bool(getattr(proposal, "requires_review", False)):
            return True
        return not bool(getattr(proposal, "requires_review", False)) and status != "requires_review"


class AccountingProposalReadyRule:
    rule_id = "accounting_proposal_ready_for_validation"
    version = "1"
    source_type = DecisionSourceType.ACCOUNTING_PROPOSAL

    def evaluate(self, proposal: Any, *, source_event_id: str | None = None) -> DecisionDraft | None:
        status = getattr(proposal, "status", "") or ""
        if status != "ready_for_validation":
            return None
        if bool(getattr(proposal, "requires_review", False)):
            # Priorité à la règle requires_review
            return None
        proposal_id = str(getattr(proposal, "proposal_id", "") or getattr(proposal, "id", ""))
        return DecisionDraft(
            decision_type=DecisionType.ACCOUNTING_PROPOSAL_READY_FOR_VALIDATION,
            source_type=DecisionSourceType.ACCOUNTING_PROPOSAL,
            source_id=proposal_id,
            severity=DecisionSeverity.MEDIUM,
            title="Proposition comptable prête à valider",
            summary="Les contrôles ont abouti : vous pouvez examiner puis valider la proposition.",
            explanation="Le statut ready_for_validation indique qu’une validation manuelle est attendue.",
            recommended_action_type=DecisionActionType.VALIDATE,
            recommended_action_path=f"/accounting/proposals/{proposal_id}",
            required_permission="ai.analysis",
            created_by_rule=self.rule_id,
            rule_version=self.version,
            deduplication_key=f"{DecisionType.ACCOUNTING_PROPOSAL_READY_FOR_VALIDATION}:{proposal_id}:v{self.version}",
            source_event_id=source_event_id,
            metadata={"status": status},
            still_active=True,
        )

    def is_resolved(self, proposal: Any) -> bool:
        status = getattr(proposal, "status", "") or ""
        return status != "ready_for_validation" or bool(getattr(proposal, "requires_review", False))


class DocumentAnalysisFailedRule:
    rule_id = "document_analysis_failed"
    version = "1"
    source_type = DecisionSourceType.DOCUMENT_ANALYSIS

    def evaluate(self, analysis: Any, *, source_event_id: str | None = None) -> DecisionDraft | None:
        status = getattr(analysis, "status", "") or ""
        if status != "failed":
            return None
        analysis_id = str(getattr(analysis, "analysis_id", "") or getattr(analysis, "id", ""))
        vault_id = str(getattr(analysis, "vault_document_id", "") or "")
        return DecisionDraft(
            decision_type=DecisionType.DOCUMENT_ANALYSIS_FAILED,
            source_type=DecisionSourceType.DOCUMENT_ANALYSIS,
            source_id=analysis_id,
            severity=DecisionSeverity.HIGH,
            title="L’analyse d’un document a échoué",
            summary="Un traitement documentaire n’a pas pu être terminé.",
            explanation="Vérifiez le document dans l’espace documentaire puis relancez le traitement si disponible.",
            recommended_action_type=DecisionActionType.OPEN_RESOURCE,
            recommended_action_path=f"/documents?document_id={vault_id}" if vault_id else "/documents",
            required_permission="documents.read",
            created_by_rule=self.rule_id,
            rule_version=self.version,
            deduplication_key=f"{DecisionType.DOCUMENT_ANALYSIS_FAILED}:{analysis_id}:v{self.version}",
            source_event_id=source_event_id,
            confidence=float(analysis.confidence) if getattr(analysis, "confidence", None) is not None else None,
            metadata={"vault_document_id": vault_id, "status": status},
            still_active=True,
        )

    def is_resolved(self, analysis: Any) -> bool:
        return (getattr(analysis, "status", "") or "") != "failed"


class DocumentAnalysisRequiresReviewRule:
    rule_id = "document_analysis_requires_review"
    version = "1"
    source_type = DecisionSourceType.DOCUMENT_ANALYSIS

    def evaluate(self, analysis: Any, *, source_event_id: str | None = None) -> DecisionDraft | None:
        status = getattr(analysis, "status", "") or ""
        requires = bool(getattr(analysis, "requires_review", False)) or status == "requires_review"
        if not requires or status == "failed":
            return None
        analysis_id = str(getattr(analysis, "analysis_id", "") or getattr(analysis, "id", ""))
        vault_id = str(getattr(analysis, "vault_document_id", "") or "")
        quality = getattr(analysis, "quality", None)
        explanation = "Une vérification humaine est recommandée sur le résultat d’analyse."
        if isinstance(quality, dict):
            band = quality.get("band") or quality.get("status")
            if band:
                explanation = f"Indicateur qualité signalé : {band}."
        return DecisionDraft(
            decision_type=DecisionType.DOCUMENT_ANALYSIS_REQUIRES_REVIEW,
            source_type=DecisionSourceType.DOCUMENT_ANALYSIS,
            source_id=analysis_id,
            severity=DecisionSeverity.MEDIUM,
            title="Document à confirmer après analyse",
            summary="L’analyse est disponible mais demande une confirmation.",
            explanation=explanation,
            recommended_action_type=DecisionActionType.REVIEW,
            recommended_action_path=f"/documents?document_id={vault_id}" if vault_id else "/documents",
            required_permission="ai.analysis",
            created_by_rule=self.rule_id,
            rule_version=self.version,
            deduplication_key=f"{DecisionType.DOCUMENT_ANALYSIS_REQUIRES_REVIEW}:{analysis_id}:v{self.version}",
            source_event_id=source_event_id,
            confidence=float(analysis.confidence) if getattr(analysis, "confidence", None) is not None else None,
            metadata={"status": status, "vault_document_id": vault_id},
            still_active=True,
        )

    def is_resolved(self, analysis: Any) -> bool:
        status = getattr(analysis, "status", "") or ""
        if status in {"completed", "failed", "blocked", "cancelled"}:
            return not bool(getattr(analysis, "requires_review", False)) or status != "requires_review"
        return not bool(getattr(analysis, "requires_review", False)) and status != "requires_review"


V1_RULES = (
    AccountingProposalRequiresReviewRule(),
    AccountingProposalReadyRule(),
    DocumentAnalysisFailedRule(),
    DocumentAnalysisRequiresReviewRule(),
)
