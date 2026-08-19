"""Handlers Event Bus → Decision Center (idempotents)."""

from __future__ import annotations

import logging

from app.accounting.accounting_models import ElfisAccountingProposal
from app.ai.ai_models import ElfisDocumentAnalysis
from app.decision_center.enums import DecisionSourceType, DecisionStatus
from app.decision_center.models import ElfisDecisionItem
from app.decision_center.rules import (
    AccountingProposalReadyRule,
    AccountingProposalRequiresReviewRule,
    DocumentAnalysisFailedRule,
    DocumentAnalysisRequiresReviewRule,
)
from app.decision_center.service import DecisionCenterService
from app.events.event_context import EventContext
from app.events.event_registry import EventHandler, EventHandlerRegistry
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames

logger = logging.getLogger(__name__)


class AccountingProposalDecisionHandler(EventHandler):
    handler_name = "decision_center_accounting_proposal_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        payload = event.payload or {}
        proposal_id = str(payload.get("proposal_id") or "").strip()
        if not proposal_id:
            return
        proposal = (
            context.db.query(ElfisAccountingProposal)
            .filter(
                ElfisAccountingProposal.organization_id == event.organization_id,
                ElfisAccountingProposal.proposal_id == proposal_id,
            )
            .one_or_none()
        )
        if proposal is None:
            return
        svc = DecisionCenterService(context.db)
        if event.event_name in {
            EventNames.ACCOUNTING_PROPOSAL_VALIDATED,
            EventNames.ACCOUNTING_PROPOSAL_REJECTED,
        }:
            svc.resolve_by_source(
                organization_id=event.organization_id,
                source_type=DecisionSourceType.ACCOUNTING_PROPOSAL,
                source_id=proposal_id,
                commit=True,
            )
            return
        for rule in (AccountingProposalRequiresReviewRule(), AccountingProposalReadyRule()):
            draft = rule.evaluate(proposal, source_event_id=str(event.event_id))
            if draft:
                svc.apply_draft(organization_id=event.organization_id, draft=draft, commit=True)
            elif rule.is_resolved(proposal):
                rows = (
                    context.db.query(ElfisDecisionItem)
                    .filter(
                        ElfisDecisionItem.organization_id == event.organization_id,
                        ElfisDecisionItem.created_by_rule == rule.rule_id,
                        ElfisDecisionItem.source_id == proposal_id,
                        ElfisDecisionItem.status.in_(
                            (DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS)
                        ),
                    )
                    .all()
                )
                for row in rows:
                    svc.repo.resolve(row)
                context.db.commit()


class DocumentAnalysisDecisionHandler(EventHandler):
    handler_name = "decision_center_document_analysis_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        payload = event.payload or {}
        analysis_id = str(payload.get("analysis_id") or "").strip()
        if not analysis_id:
            return
        analysis = (
            context.db.query(ElfisDocumentAnalysis)
            .filter(
                ElfisDocumentAnalysis.organization_id == event.organization_id,
                ElfisDocumentAnalysis.analysis_id == analysis_id,
            )
            .one_or_none()
        )
        if analysis is None:
            return
        svc = DecisionCenterService(context.db)
        if event.event_name == EventNames.DOCUMENT_ANALYSIS_COMPLETED and not bool(
            getattr(analysis, "requires_review", False)
        ):
            svc.resolve_by_source(
                organization_id=event.organization_id,
                source_type=DecisionSourceType.DOCUMENT_ANALYSIS,
                source_id=analysis_id,
                commit=True,
            )
            # Peut encore générer requires_review si flag true — déjà exclu
            return
        for rule in (DocumentAnalysisFailedRule(), DocumentAnalysisRequiresReviewRule()):
            draft = rule.evaluate(analysis, source_event_id=str(event.event_id))
            if draft:
                svc.apply_draft(organization_id=event.organization_id, draft=draft, commit=True)


def register_decision_center_handlers(registry: EventHandlerRegistry) -> None:
    accounting_handler = AccountingProposalDecisionHandler()
    for name in (
        EventNames.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
        EventNames.ACCOUNTING_PROPOSAL_READY,
        EventNames.ACCOUNTING_PROPOSAL_UPDATED,
        EventNames.ACCOUNTING_PROPOSAL_VALIDATED,
        EventNames.ACCOUNTING_PROPOSAL_REJECTED,
        EventNames.ACCOUNTING_PROPOSAL_REOPENED,
        EventNames.ACCOUNTING_PROPOSAL_CREATED,
    ):
        if not any(
            h.handler_name == accounting_handler.handler_name for h in registry.get_handlers(name)
        ):
            registry.register(name, accounting_handler)

    doc_handler = DocumentAnalysisDecisionHandler()
    for name in (
        EventNames.DOCUMENT_ANALYSIS_FAILED,
        EventNames.DOCUMENT_ANALYSIS_COMPLETED,
    ):
        if not any(h.handler_name == doc_handler.handler_name for h in registry.get_handlers(name)):
            registry.register(name, doc_handler)
