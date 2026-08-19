"""Phase C — Idempotence (IDEMP-001 … IDEMP-003)."""

from __future__ import annotations

from app.document_intelligence.event_handlers import DocumentArchivedTextExtractionHandler
from app.events.event_context import EventContext
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames
from tests.document_intelligence import setup_di_db


def test_idemp_job_handler_double_event():
    db, _, _ = setup_di_db()
    from app.config import settings
    from unittest.mock import patch

    with patch.object(settings, "elfis_auto_text_extraction_enabled", True):
        handler = DocumentArchivedTextExtractionHandler()
        event = DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
            organization_id=1,
            aggregate_type="vault_document",
            aggregate_id="vd-idemp",
            payload={"vault_document_id": "vd-idemp", "version": 1},
            metadata={},
        )
        ctx = EventContext(db=db, worker_id="idemp")
        handler.handle(event, ctx)
        handler.handle(event, ctx)
        jobs = db.query(ElfisJob).filter(ElfisJob.job_name == JobNames.VAULT_DOCUMENT_EXTRACT_TEXT).all()
        assert len(jobs) == 1
