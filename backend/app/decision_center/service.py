"""Service Decision Center — sync, permissions, mutations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.accounting.accounting_models import ElfisAccountingProposal
from app.ai.ai_models import ElfisDocumentAnalysis
from app.decision_center.actions import build_available_actions
from app.decision_center.enums import DecisionActionType, DecisionStatus
from app.decision_center.evidence import build_evidence
from app.decision_center.models import ElfisDecisionExecutionAttempt, ElfisDecisionItem
from app.decision_center.repository import DecisionRepository
from app.decision_center.rules import (
    AccountingProposalReadyRule,
    AccountingProposalRequiresReviewRule,
    DocumentAnalysisFailedRule,
    DocumentAnalysisRequiresReviewRule,
)
from app.decision_center.schemas import (
    CommandDecisionInsightOut,
    DecisionDetailOut,
    DecisionEvidenceOut,
    DecisionHistoryItemOut,
    DecisionListOut,
    DecisionOut,
)
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.services.auth import write_audit

logger = logging.getLogger(__name__)

# Sync ciblé : plafonds pour rester rapide
_MAX_PROPOSALS_SCAN = 100
_MAX_ANALYSES_SCAN = 100


class DecisionCenterService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DecisionRepository(db)
        self._review_rule = AccountingProposalRequiresReviewRule()
        self._ready_rule = AccountingProposalReadyRule()
        self._failed_rule = DocumentAnalysisFailedRule()
        self._doc_review_rule = DocumentAnalysisRequiresReviewRule()

    # ------------------------------------------------------------------
    # Sync / backfill
    # ------------------------------------------------------------------

    def sync_open_decisions(self, organization_id: int) -> dict[str, int]:
        """Évalue les ressources existantes de l’org (pas un scan global)."""
        stats = {"created": 0, "updated": 0, "resolved": 0, "reopened": 0}
        stats = self._merge_stats(stats, self._sync_proposals(organization_id))
        stats = self._merge_stats(stats, self._sync_analyses(organization_id))
        self.db.commit()
        return stats

    def _merge_stats(self, a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
        return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}

    def _sync_proposals(self, organization_id: int) -> dict[str, int]:
        stats = {"created": 0, "updated": 0, "resolved": 0, "reopened": 0}
        proposals = (
            self.db.query(ElfisAccountingProposal)
            .filter(ElfisAccountingProposal.organization_id == organization_id)
            .order_by(ElfisAccountingProposal.updated_at.desc())
            .limit(_MAX_PROPOSALS_SCAN)
            .all()
        )
        for proposal in proposals:
            for rule in (self._review_rule, self._ready_rule):
                draft = rule.evaluate(proposal)
                if draft is None:
                    open_rows = (
                        self.db.query(ElfisDecisionItem)
                        .filter(
                            ElfisDecisionItem.organization_id == organization_id,
                            ElfisDecisionItem.source_type == rule.source_type,
                            ElfisDecisionItem.source_id
                            == str(getattr(proposal, "proposal_id", "")),
                            ElfisDecisionItem.created_by_rule == rule.rule_id,
                            ElfisDecisionItem.status.in_(
                                (DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS)
                            ),
                        )
                        .all()
                    )
                    if rule.is_resolved(proposal):
                        for row in open_rows:
                            self.repo.resolve(row)
                            stats["resolved"] += 1
                            self._publish(EventNames.DECISION_RESOLVED, row)
                    continue
                row, event = self.repo.upsert_from_draft(
                    organization_id=organization_id, draft=draft
                )
                if event == "created":
                    stats["created"] += 1
                    self._publish(EventNames.DECISION_CREATED, row)
                elif event == "updated":
                    stats["updated"] += 1
                    self._publish(EventNames.DECISION_UPDATED, row)
                elif event == "reopened":
                    stats["reopened"] += 1
                    self._publish(EventNames.DECISION_UPDATED, row)
        return stats

    def _sync_analyses(self, organization_id: int) -> dict[str, int]:
        stats = {"created": 0, "updated": 0, "resolved": 0, "reopened": 0}
        analyses = (
            self.db.query(ElfisDocumentAnalysis)
            .filter(ElfisDocumentAnalysis.organization_id == organization_id)
            .order_by(ElfisDocumentAnalysis.created_at.desc())
            .limit(_MAX_ANALYSES_SCAN)
            .all()
        )
        for analysis in analyses:
            for rule in (self._failed_rule, self._doc_review_rule):
                draft = rule.evaluate(analysis)
                if draft is None:
                    open_rows = (
                        self.db.query(ElfisDecisionItem)
                        .filter(
                            ElfisDecisionItem.organization_id == organization_id,
                            ElfisDecisionItem.source_type == rule.source_type,
                            ElfisDecisionItem.source_id
                            == str(getattr(analysis, "analysis_id", "")),
                            ElfisDecisionItem.created_by_rule == rule.rule_id,
                            ElfisDecisionItem.status.in_(
                                (DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS)
                            ),
                        )
                        .all()
                    )
                    if rule.is_resolved(analysis):
                        for row in open_rows:
                            self.repo.resolve(row)
                            stats["resolved"] += 1
                            self._publish(EventNames.DECISION_RESOLVED, row)
                    continue
                row, event = self.repo.upsert_from_draft(
                    organization_id=organization_id, draft=draft
                )
                if event == "created":
                    stats["created"] += 1
                    self._publish(EventNames.DECISION_CREATED, row)
                elif event == "updated":
                    stats["updated"] += 1
                    self._publish(EventNames.DECISION_UPDATED, row)
                elif event == "reopened":
                    stats["reopened"] += 1
                    self._publish(EventNames.DECISION_UPDATED, row)
        return stats

    def apply_draft(
        self, *, organization_id: int, draft, commit: bool = True
    ) -> ElfisDecisionItem:
        row, event = self.repo.upsert_from_draft(organization_id=organization_id, draft=draft)
        if event == "created":
            self._publish(EventNames.DECISION_CREATED, row)
        elif event in {"updated", "reopened"}:
            self._publish(EventNames.DECISION_UPDATED, row)
        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row

    def resolve_by_source(
        self,
        *,
        organization_id: int,
        source_type: str,
        source_id: str,
        commit: bool = True,
    ) -> int:
        rows = (
            self.db.query(ElfisDecisionItem)
            .filter(
                ElfisDecisionItem.organization_id == organization_id,
                ElfisDecisionItem.source_type == source_type,
                ElfisDecisionItem.source_id == source_id,
                ElfisDecisionItem.status.in_(
                    (DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS)
                ),
            )
            .all()
        )
        for row in rows:
            self.repo.resolve(row)
            self._publish(EventNames.DECISION_RESOLVED, row)
        if commit:
            self.db.commit()
        return len(rows)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def list_for_user(
        self,
        *,
        organization_id: int,
        permissions: list[str],
        status: str | None = None,
        severity: str | None = None,
        source_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
        sync: bool = True,
    ) -> DecisionListOut:
        if sync:
            try:
                self.sync_open_decisions(organization_id)
            except Exception:
                logger.exception("decision_sync_failed org=%s", organization_id)
                self.db.rollback()

        rows, total = self.repo.list_decisions(
            organization_id=organization_id,
            status=status,
            severity=severity,
            source_type=source_type,
            page=page,
            page_size=page_size,
        )
        visible = [r for r in rows if self._can_view(r, permissions)]
        return DecisionListOut(
            items=[self.to_out(r, permissions) for r in visible],
            total=len(visible) if len(visible) != len(rows) else total,
            page=page,
            page_size=page_size,
        )

    def get_for_user(
        self, *, organization_id: int, decision_id: str, permissions: list[str]
    ) -> DecisionOut:
        return self.get_detail(
            organization_id=organization_id,
            decision_id=decision_id,
            permissions=permissions,
            sync=True,
        )

    def get_detail(
        self,
        *,
        organization_id: int,
        decision_id: str,
        permissions: list[str],
        sync: bool = True,
    ) -> DecisionDetailOut:
        if sync:
            try:
                self.sync_open_decisions(organization_id)
            except Exception:
                logger.exception("decision_sync_failed_detail org=%s", organization_id)
                self.db.rollback()

        row = self.repo.get(organization_id=organization_id, decision_id=decision_id)
        if row is None:
            raise HTTPException(404, detail="Décision introuvable")
        if not self._can_view(row, permissions):
            raise HTTPException(403, detail="Permission insuffisante")

        source = self.load_source(row)
        base = self.to_out(row, permissions, source=source)
        evidence = [
            DecisionEvidenceOut(**item) for item in build_evidence(source_type=row.source_type, source=source)
        ]
        history = self._history(row)
        copy = self._user_facing_copy(row)
        return DecisionDetailOut(
            **base.model_dump(),
            evidence=evidence,
            history=history,
            source_label=copy["source_label"],
            what_was_detected=copy["what_was_detected"],
            why_it_matters=copy["why_it_matters"],
            what_to_do=copy["what_to_do"],
            what_happens_after=copy["what_happens_after"],
        )

    def load_source(self, row: ElfisDecisionItem) -> Any | None:
        if row.source_type == "accounting_proposal":
            return (
                self.db.query(ElfisAccountingProposal)
                .filter(
                    ElfisAccountingProposal.organization_id == row.organization_id,
                    ElfisAccountingProposal.proposal_id == row.source_id,
                )
                .one_or_none()
            )
        if row.source_type == "document_analysis":
            return (
                self.db.query(ElfisDocumentAnalysis)
                .filter(
                    ElfisDocumentAnalysis.organization_id == row.organization_id,
                    ElfisDocumentAnalysis.analysis_id == row.source_id,
                )
                .one_or_none()
            )
        return None

    def dismiss(
        self,
        *,
        organization_id: int,
        decision_id: str,
        permissions: list[str],
        user_id: int | None,
    ) -> DecisionOut:
        row = self.repo.get(organization_id=organization_id, decision_id=decision_id)
        if row is None:
            raise HTTPException(404, detail="Décision introuvable")
        if not self._can_view(row, permissions):
            raise HTTPException(403, detail="Permission insuffisante")
        if row.status != DecisionStatus.OPEN and row.status != DecisionStatus.IN_PROGRESS:
            raise HTTPException(409, detail="La décision n’est plus ouverte")
        if row.status == DecisionStatus.IN_PROGRESS:
            # Autoriser dismiss depuis in_progress aussi
            pass
        self.repo.dismiss(row)
        self._publish(EventNames.DECISION_DISMISSED, row)
        write_audit(
            self.db,
            user_id=user_id,
            organization_id=organization_id,
            action=f"decision.dismiss:{row.id}",
            module="decision_center",
        )
        self.db.commit()
        self.db.refresh(row)
        return self.to_out(row, permissions)

    def insights_for_command_center(
        self, *, organization_id: int, permissions: list[str], limit: int = 3
    ) -> list[CommandDecisionInsightOut]:
        """Sync léger + top N décisions ouvertes visibles."""
        try:
            self.sync_open_decisions(organization_id)
        except Exception:
            logger.exception("decision_sync_failed_cc org=%s", organization_id)
            self.db.rollback()

        rows = self.repo.list_open_prioritized(organization_id=organization_id, limit=limit * 3)
        insights: list[CommandDecisionInsightOut] = []
        for row in rows:
            if not self._can_view(row, permissions):
                continue
            # Lien vers détail décision (exécution) plutôt que path métier seul
            insights.append(
                CommandDecisionInsightOut(
                    decision_id=row.id,
                    title=row.title,
                    summary=row.summary,
                    severity=row.severity,
                    action_label="Examiner",
                    action_path=f"/decisions/{row.id}",
                )
            )
            if len(insights) >= limit:
                break
        return insights

    def to_out(
        self,
        row: ElfisDecisionItem,
        permissions: list[str],
        *,
        source: Any | None = None,
    ) -> DecisionOut:
        if source is None and row.status in {DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS}:
            source = self.load_source(row)
        return DecisionOut(
            id=row.id,
            organization_id=row.organization_id,
            decision_type=row.decision_type,
            source_type=row.source_type,
            source_id=row.source_id,
            status=row.status,
            severity=row.severity,
            confidence=float(row.confidence) if row.confidence is not None else None,
            title=row.title,
            summary=row.summary,
            explanation=row.explanation,
            recommended_action_type=row.recommended_action_type,
            recommended_action_path=row.recommended_action_path,
            required_permission=row.required_permission,
            created_by_rule=row.created_by_rule,
            rule_version=row.rule_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            resolved_at=row.resolved_at,
            dismissed_at=row.dismissed_at,
            available_actions=build_available_actions(
                row=row,
                permissions=permissions,
                allows=self._allows,
                source=source,
            ),
            metadata=row.metadata_json if isinstance(row.metadata_json, dict) else None,
            execution_status=getattr(row, "execution_status", None) or "idle",
            last_action_type=getattr(row, "last_action_type", None),
            last_execution_error_code=getattr(row, "last_execution_error_code", None),
            last_execution_error_message=getattr(row, "last_execution_error_message", None),
            execution_attempts=int(getattr(row, "execution_attempts", 0) or 0),
            last_source_refresh_at=getattr(row, "last_source_refresh_at", None),
        )

    def _history(self, row: ElfisDecisionItem, *, limit: int = 20) -> list[DecisionHistoryItemOut]:
        items: list[DecisionHistoryItemOut] = [
            DecisionHistoryItemOut(
                id=f"created-{row.id}",
                kind="created",
                label="Décision créée",
                status=None,
                action_type=None,
                at=row.created_at,
                user_id=None,
            )
        ]
        attempts = (
            self.db.query(ElfisDecisionExecutionAttempt)
            .filter(ElfisDecisionExecutionAttempt.decision_id == row.id)
            .order_by(ElfisDecisionExecutionAttempt.started_at.desc())
            .limit(limit)
            .all()
        )
        for attempt in reversed(attempts):
            label = {
                "running": "Exécution démarrée",
                "succeeded": "Exécution réussie",
                "failed": "Exécution échouée",
                "cancelled": "Exécution annulée",
            }.get(attempt.status, "Exécution")
            items.append(
                DecisionHistoryItemOut(
                    id=attempt.id,
                    kind=f"execution_{attempt.status}",
                    label=label,
                    status=attempt.status,
                    action_type=attempt.action_type,
                    at=attempt.completed_at or attempt.started_at,
                    user_id=attempt.user_id,
                    error_message=attempt.error_message,
                )
            )
        if row.resolved_at:
            items.append(
                DecisionHistoryItemOut(
                    id=f"resolved-{row.id}",
                    kind="resolved",
                    label="Décision résolue",
                    status="resolved",
                    at=row.resolved_at,
                )
            )
        if row.dismissed_at:
            items.append(
                DecisionHistoryItemOut(
                    id=f"dismissed-{row.id}",
                    kind="dismissed",
                    label="Décision ignorée",
                    status="dismissed",
                    at=row.dismissed_at,
                    user_id=getattr(row, "last_action_by_user_id", None),
                )
            )
        items.sort(key=lambda x: x.at)
        return items[-limit:]

    @staticmethod
    def _user_facing_copy(row: ElfisDecisionItem) -> dict[str, str]:
        if row.source_type == "accounting_proposal":
            return {
                "source_label": "Proposition comptable",
                "what_was_detected": row.summary,
                "why_it_matters": "Une validation incorrecte pourrait fausser les écritures.",
                "what_to_do": "Examiner la proposition, corriger si besoin, puis valider.",
                "what_happens_after": "Lorsque la proposition est validée ou rejetée, cette décision se résout automatiquement.",
            }
        return {
            "source_label": "Analyse documentaire",
            "what_was_detected": row.summary,
            "why_it_matters": "Un document mal traité peut bloquer la suite comptable.",
            "what_to_do": "Examiner le document et relancer l’analyse si disponible.",
            "what_happens_after": "Quand l’analyse n’est plus en échec ou ne demande plus de revue, la décision se résout.",
        }

    def _can_view(self, row: ElfisDecisionItem, permissions: list[str]) -> bool:
        if row.source_type == "accounting_proposal":
            return self._allows(permissions, "ai.analysis") or self._allows(
                permissions, "documents.read"
            ) or self._allows(permissions, "invoice.read")
        if row.source_type == "document_analysis":
            return self._allows(permissions, "documents.read") or self._allows(
                permissions, "ai.analysis"
            )
        return True

    @staticmethod
    def _action_label(action_type: str | None) -> str:
        mapping = {
            DecisionActionType.REVIEW: "Examiner",
            DecisionActionType.VALIDATE: "Valider",
            DecisionActionType.CORRECT: "Corriger",
            DecisionActionType.RETRY: "Relancer",
            DecisionActionType.OPEN_RESOURCE: "Ouvrir",
            DecisionActionType.DISMISS: "Ignorer",
            DecisionActionType.OPEN_ACCOUNTING_PROPOSAL: "Examiner",
            DecisionActionType.OPEN_DOCUMENT: "Examiner",
            DecisionActionType.VALIDATE_ACCOUNTING_PROPOSAL: "Valider",
            DecisionActionType.RETRY_DOCUMENT_ANALYSIS: "Relancer",
        }
        return mapping.get(action_type or "", "Ouvrir")

    @staticmethod
    def _allows(permissions: list[str], permission: str) -> bool:
        if not permission:
            return True
        if "*" in permissions:
            return True
        if permission in permissions:
            return True
        if permission == "ai.analysis" and (
            "ai.analysis" in permissions or "accounting.view" in permissions
        ):
            return True
        if permission == "documents.read" and (
            "documents.read" in permissions or "documents.*" in permissions
        ):
            return True
        if permission == "documents.write" and (
            "documents.write" in permissions or "documents.*" in permissions
        ):
            return True
        if permission.startswith("accounting."):
            action = permission.split(".", 1)[1]
            fallbacks = {
                "view": {"ai.analysis", "documents.read", "invoice.read", "accounting.view"},
                "edit": {"ai.analysis", "documents.write", "invoice.create", "accounting.edit"},
                "validate": {"ai.analysis", "documents.write", "accounting.validate"},
                "reject": {"ai.analysis", "documents.write", "accounting.reject"},
                "reopen": {"ai.analysis", "documents.write", "accounting.reopen"},
            }
            if set(permissions) & fallbacks.get(action, set()):
                return True
        return False

    def _publish(self, event_name: str, row: ElfisDecisionItem) -> None:
        try:
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=event_name,
                    organization_id=row.organization_id,
                    aggregate_type="decision",
                    aggregate_id=row.id,
                    payload={
                        "decision_id": row.id,
                        "decision_type": row.decision_type,
                        "status": row.status,
                        "severity": row.severity,
                        "source_type": row.source_type,
                        "source_id": row.source_id,
                    },
                    idempotency_key=f"{event_name}:{row.id}:{row.status}:{int((row.updated_at or row.created_at).timestamp()) if (row.updated_at or row.created_at) else 0}",
                ),
            )
        except Exception:
            logger.exception("decision_event_publish_failed id=%s", row.id)
