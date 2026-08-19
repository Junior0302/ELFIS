"""Event Bus ↔ Document Intelligence."""

from __future__ import annotations

import logging

from app.config import settings
from app.events.event_context import EventContext
from app.events.event_registry import EventHandler
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames

logger = logging.getLogger(__name__)


class DocumentArchivedTextExtractionHandler(EventHandler):
    """vault.document.archived.v1 → enqueue extract_text (best-effort)."""

    handler_name = "document_archived_text_extraction_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if not settings.elfis_auto_text_extraction_enabled:
            return
        if event.event_name != EventNames.VAULT_DOCUMENT_ARCHIVED:
            return
        payload = event.payload or {}
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        if not vault_document_id:
            return
        org_id = event.organization_id
        version = int(payload.get("version") or payload.get("document_version") or 1)
        idem = f"document-text:{org_id}:{vault_document_id}:{version}"
        try:
            JobService(context.db).enqueue(
                JobRequest(
                    job_name=JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
                    organization_id=org_id,
                    user_id=_actor(event),
                    payload={
                        "vault_document_id": vault_document_id,
                        "document_version": version,
                        "idempotency_key": idem,
                    },
                    idempotency_key=idem,
                    correlation_id=str(event.correlation_id) if event.correlation_id else None,
                    causation_event_id=str(event.event_id),
                )
            )
        except Exception:
            logger.exception(
                "document_text_extraction_enqueue_failed",
                extra={
                    "vault_document_id": vault_document_id,
                    "organization_id": org_id,
                    "event_id": str(event.event_id),
                },
            )


class DocumentExtractionCompletedAIHandler(EventHandler):
    """document.extraction.completed.v1 → enqueue AI classification."""

    handler_name = "document_extraction_completed_ai_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if not settings.elfis_auto_ai_analysis_enabled:
            return
        if event.event_name != EventNames.DOCUMENT_EXTRACTION_COMPLETED:
            return
        payload = event.payload or {}
        extraction_id = str(payload.get("extraction_id") or "").strip()
        vault_document_id = str(payload.get("vault_document_id") or "").strip()
        org_id = event.organization_id
        if not extraction_id or not vault_document_id:
            return
        if int(payload.get("text_length") or 0) <= 0:
            return
        if payload.get("requires_ocr"):
            return

        from app.ai.ai_models import ElfisDocumentAnalysis
        from app.ai.ai_repository import AIRepository
        from app.ai.ai_types import DocumentAnalysisStatus
        from app.document_intelligence.document_service import DocumentIntelligenceService
        import uuid
        from datetime import datetime

        try:
            svc = DocumentIntelligenceService(context.db)
            extraction = svc.get_extraction(extraction_id)
            if extraction.organization_id != org_id:
                return
            if not (extraction.text_content or "").strip():
                return

            version = int(extraction.document_version or 1)
            repo = AIRepository(context.db)
            analysis = repo.find_analysis_for_document(
                organization_id=org_id,
                vault_document_id=vault_document_id,
                document_version=version,
            )
            now = datetime.utcnow()
            if analysis is None:
                analysis = ElfisDocumentAnalysis(
                    id=str(uuid.uuid4()),
                    analysis_id=str(uuid.uuid4()),
                    organization_id=org_id,
                    vault_document_id=vault_document_id,
                    document_version=version,
                    status=DocumentAnalysisStatus.CLASSIFYING,
                    current_stage="classification",
                    requires_review=False,
                    ai_execution_ids=[],
                    created_at=now,
                    updated_at=now,
                )
            else:
                if analysis.status not in (
                    DocumentAnalysisStatus.FAILED,
                    DocumentAnalysisStatus.BLOCKED,
                    DocumentAnalysisStatus.PENDING,
                ):
                    # Analyse déjà en cours / terminée
                    if analysis.status in (
                        DocumentAnalysisStatus.CLASSIFYING,
                        DocumentAnalysisStatus.EXTRACTING,
                        DocumentAnalysisStatus.VALIDATING,
                        DocumentAnalysisStatus.COMPLETED,
                        DocumentAnalysisStatus.REQUIRES_REVIEW,
                    ):
                        return
                analysis.status = DocumentAnalysisStatus.CLASSIFYING
                analysis.current_stage = "classification"
            repo.save_analysis(analysis)

            JobService(context.db).enqueue(
                JobRequest(
                    job_name=JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION,
                    organization_id=org_id,
                    payload={
                        "vault_document_id": vault_document_id,
                        "analysis_id": analysis.analysis_id,
                        "extraction_id": extraction_id,
                        "filename": extraction.filename,
                        "mime_type": extraction.mime_type,
                        "document_version": version,
                    },
                    idempotency_key=f"ai-classify:{org_id}:{vault_document_id}:{version}",
                    correlation_id=str(event.correlation_id) if event.correlation_id else None,
                    causation_event_id=str(event.event_id),
                )
            )
        except Exception:
            logger.exception(
                "document_extraction_ai_enqueue_failed",
                extra={
                    "extraction_id": extraction_id,
                    "vault_document_id": vault_document_id,
                    "organization_id": org_id,
                },
            )


def _actor(event: DomainEvent) -> int | None:
    raw = (event.metadata or {}).get("actor_user_id")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
