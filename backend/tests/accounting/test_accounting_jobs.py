"""Tests jobs + events Accounting."""

from __future__ import annotations

from app.accounting.accounting_types import SUPPORTED_DOCUMENT_TYPES_V1
from app.config import settings
from app.events.event_context import EventContext
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.handlers.accounting_event_handlers import DocumentAnalysisCompletedAccountingHandler
from app.jobs.job_models import ElfisJob
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.job_worker import JobWorker
from tests.accounting import seed_analysis, setup_acc_db


def test_build_proposal_job_light_result():
    db, Session, _ = setup_acc_db()
    seed_analysis(db)
    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.ACCOUNTING_BUILD_PROPOSAL,
            organization_id=1,
            user_id=1,
            payload={"vault_document_id": "vd-acc", "document_version": 1},
            idempotency_key="acc-job-1",
        )
    )
    worker = JobWorker(db, worker_id="w-acc", session_factory=lambda: Session())
    worker.process_next_batch()
    job = db.query(ElfisJob).filter_by(idempotency_key="acc-job-1").one()
    assert job.status == JobStatus.COMPLETED
    result = job.result or {}
    assert "proposal_id" in result
    assert "lines" not in result
    assert "extracted_text" not in result


def test_analysis_completed_enqueues_job(monkeypatch):
    db, _, _ = setup_acc_db()
    monkeypatch.setattr(settings, "elfis_auto_accounting_proposal_enabled", True)
    handler = DocumentAnalysisCompletedAccountingHandler()
    event = DomainEvent(
        event_name=EventNames.DOCUMENT_ANALYSIS_COMPLETED,
        organization_id=1,
        aggregate_type="document_analysis",
        aggregate_id="a1",
        payload={
            "analysis_id": "a1",
            "vault_document_id": "vd-acc",
            "document_type": "supplier_invoice",
            "document_version": 1,
            "status": "completed",
        },
        metadata={},
    )
    handler.handle(event, EventContext(db=db, worker_id="t"))
    jobs = db.query(ElfisJob).filter_by(job_name=JobNames.ACCOUNTING_BUILD_PROPOSAL).all()
    assert len(jobs) == 1
    assert jobs[0].idempotency_key == "accounting-proposal:1:vd-acc:1"
    handler.handle(event, EventContext(db=db, worker_id="t"))
    assert db.query(ElfisJob).filter_by(job_name=JobNames.ACCOUNTING_BUILD_PROPOSAL).count() == 1


def test_unsupported_type_skipped(monkeypatch):
    db, _, _ = setup_acc_db()
    monkeypatch.setattr(settings, "elfis_auto_accounting_proposal_enabled", True)
    handler = DocumentAnalysisCompletedAccountingHandler()
    event = DomainEvent(
        event_name=EventNames.DOCUMENT_ANALYSIS_COMPLETED,
        organization_id=1,
        aggregate_type="document_analysis",
        aggregate_id="a1",
        payload={
            "vault_document_id": "vd-acc",
            "document_type": "quote",
            "document_version": 1,
        },
        metadata={},
    )
    handler.handle(event, EventContext(db=db, worker_id="t"))
    assert db.query(ElfisJob).count() == 0
    assert "quote" not in SUPPORTED_DOCUMENT_TYPES_V1
