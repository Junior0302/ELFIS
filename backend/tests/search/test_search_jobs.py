"""Tests jobs + events Search."""

from __future__ import annotations

from app.config import settings
from app.events.event_context import EventContext
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.handlers.search_event_handlers import VaultArchivedSearchIndexHandler
from app.jobs.job_models import ElfisJob
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.job_worker import JobWorker
from app.search.search_types import SearchResourceTypes
from tests.search import setup_search_db


def test_index_job_light_result():
    db, Session, _ = setup_search_db()
    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.SEARCH_INDEX_RESOURCE,
            organization_id=1,
            payload={
                "resource_type": SearchResourceTypes.VAULT_DOCUMENT,
                "resource_id": "vd-1",
                "resource_version": 1,
            },
            idempotency_key="search-job-1",
        )
    )
    worker = JobWorker(db, worker_id="w-s", session_factory=lambda: Session())
    assert worker.process_next_batch() >= 1
    job = db.query(ElfisJob).filter_by(idempotency_key="search-job-1").one()
    assert job.status == JobStatus.COMPLETED
    result = job.result or {}
    assert result.get("indexed") is True
    assert "search_document_id" in result
    assert "search_text" not in result


def test_vault_event_enqueues_index(monkeypatch):
    db, _, _ = setup_search_db()
    monkeypatch.setattr(settings, "elfis_auto_search_indexing_enabled", True)
    handler = VaultArchivedSearchIndexHandler()
    event = DomainEvent(
        event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
        organization_id=1,
        aggregate_type="vault_document",
        aggregate_id="vd-1",
        payload={"vault_document_id": "vd-1", "version": 1},
        metadata={},
    )
    handler.handle(event, EventContext(db=db, worker_id="t"))
    jobs = db.query(ElfisJob).filter(ElfisJob.job_name == JobNames.SEARCH_INDEX_RESOURCE).all()
    assert len(jobs) == 1
    handler.handle(event, EventContext(db=db, worker_id="t"))
    jobs2 = db.query(ElfisJob).filter(ElfisJob.job_name == JobNames.SEARCH_INDEX_RESOURCE).all()
    assert len(jobs2) == 1
