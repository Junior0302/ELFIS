"""ELFIS Event Bus V1 — publication durable + worker DB."""

from __future__ import annotations

from app.events.event_bus import DatabaseEventBus, EventBus, get_event_bus, safe_publish
from app.events.event_registry import EventHandler, EventHandlerRegistry, default_registry
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.event_worker import EventWorker, compute_retry_delay_seconds


_handlers_bootstrapped = False


def bootstrap_handlers(registry: EventHandlerRegistry | None = None) -> None:
    """Enregistre les handlers applicatifs (idempotent)."""
    global _handlers_bootstrapped
    reg = registry or default_registry
    if registry is None and _handlers_bootstrapped:
        return
    from app.events.handlers.document_handlers import DocumentArchivedAuditHandler
    from app.jobs.handlers.event_bridge import DocumentArchivedMetadataJobHandler
    from app.document_intelligence.event_handlers import (
        DocumentArchivedTextExtractionHandler,
        DocumentExtractionCompletedAIHandler,
    )
    from app.events.handlers.accounting_event_handlers import (
        DocumentAnalysisCompletedAccountingHandler,
    )
    from app.events.handlers.search_event_handlers import (
        AccountingProposalSearchIndexHandler,
        AnalysisCompletedSearchIndexHandler,
        ExtractionCompletedSearchIndexHandler,
        SalesCrmSearchIndexHandler,
        VaultArchivedSearchIndexHandler,
    )
    from app.notifications import register_notification_handlers
    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()

    handler = DocumentArchivedAuditHandler()
    existing = [
        h
        for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)
        if h.handler_name == handler.handler_name
    ]
    if not existing:
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, handler)

    meta_handler = DocumentArchivedMetadataJobHandler()
    meta_existing = [
        h
        for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)
        if h.handler_name == meta_handler.handler_name
    ]
    if not meta_existing:
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, meta_handler)

    text_handler = DocumentArchivedTextExtractionHandler()
    text_existing = [
        h
        for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)
        if h.handler_name == text_handler.handler_name
    ]
    if not text_existing:
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, text_handler)

    search_vault = VaultArchivedSearchIndexHandler()
    if not any(
        h.handler_name == search_vault.handler_name
        for h in reg.get_handlers(EventNames.VAULT_DOCUMENT_ARCHIVED)
    ):
        reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, search_vault)

    ai_from_extraction = DocumentExtractionCompletedAIHandler()
    ai_existing = [
        h
        for h in reg.get_handlers(EventNames.DOCUMENT_EXTRACTION_COMPLETED)
        if h.handler_name == ai_from_extraction.handler_name
    ]
    if not ai_existing:
        reg.register(EventNames.DOCUMENT_EXTRACTION_COMPLETED, ai_from_extraction)

    search_extraction = ExtractionCompletedSearchIndexHandler()
    if not any(
        h.handler_name == search_extraction.handler_name
        for h in reg.get_handlers(EventNames.DOCUMENT_EXTRACTION_COMPLETED)
    ):
        reg.register(EventNames.DOCUMENT_EXTRACTION_COMPLETED, search_extraction)

    accounting_from_analysis = DocumentAnalysisCompletedAccountingHandler()
    acc_existing = [
        h
        for h in reg.get_handlers(EventNames.DOCUMENT_ANALYSIS_COMPLETED)
        if h.handler_name == accounting_from_analysis.handler_name
    ]
    if not acc_existing:
        reg.register(EventNames.DOCUMENT_ANALYSIS_COMPLETED, accounting_from_analysis)

    search_analysis = AnalysisCompletedSearchIndexHandler()
    if not any(
        h.handler_name == search_analysis.handler_name
        for h in reg.get_handlers(EventNames.DOCUMENT_ANALYSIS_COMPLETED)
    ):
        reg.register(EventNames.DOCUMENT_ANALYSIS_COMPLETED, search_analysis)

    accounting_search = AccountingProposalSearchIndexHandler()
    for ev in (
        EventNames.ACCOUNTING_PROPOSAL_READY,
        EventNames.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
        EventNames.ACCOUNTING_PROPOSAL_UPDATED,
        EventNames.ACCOUNTING_PROPOSAL_VALIDATED,
        EventNames.ACCOUNTING_PROPOSAL_REJECTED,
    ):
        if not any(h.handler_name == accounting_search.handler_name for h in reg.get_handlers(ev)):
            reg.register(ev, accounting_search)

    register_notification_handlers(reg)

    from app.events.handlers.billing_event_handlers import register_billing_event_handlers

    register_billing_event_handlers(reg)

    from app.events.handlers.banking_event_handlers import register_banking_event_handlers

    register_banking_event_handlers(reg)

    from app.decision_center.event_handlers import register_decision_center_handlers

    register_decision_center_handlers(reg)

    sales_search = SalesCrmSearchIndexHandler()
    for ev in (
        EventNames.SALES_LEAD_CREATED,
        EventNames.SALES_COMPANY_CREATED,
        EventNames.SALES_PERSON_CREATED,
        EventNames.SALES_OPPORTUNITY_CREATED,
        EventNames.SALES_OPPORTUNITY_UPDATED,
        EventNames.SALES_OPPORTUNITY_STAGE_CHANGED,
        EventNames.SALES_ACTIVITY_CREATED,
        EventNames.SALES_TASK_CREATED,
        EventNames.SALES_TASK_COMPLETED,
    ):
        if not any(h.handler_name == sales_search.handler_name for h in reg.get_handlers(ev)):
            reg.register(ev, sales_search)

    if registry is None:
        _handlers_bootstrapped = True


__all__ = [
    "DatabaseEventBus",
    "DomainEvent",
    "EventBus",
    "EventHandler",
    "EventHandlerRegistry",
    "EventNames",
    "EventWorker",
    "bootstrap_handlers",
    "compute_retry_delay_seconds",
    "default_registry",
    "get_event_bus",
    "safe_publish",
]
