"""Tests orchestration / retry / cancel / timeout."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.document_processing.orchestrator import DocumentProcessingOrchestrator
from app.document_processing.policies import ProcessingRetryPolicy
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.service import DocumentProcessingService
from app.document_processing.types import ProcessingJobStatus, ProcessingStepStatus
from tests.document_processing.conftest_helpers import make_processing_db, seed_document, seed_org_user


def _run(coro):
    return asyncio.run(coro)


def test_full_pipeline_completes(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(organization_id=org.id, document_id=doc.id)
    repo = DocumentProcessingRepository(db)
    claimed = repo.claim_jobs(worker_id="w1", batch_size=1, lease_seconds=60)
    assert len(claimed) == 1
    orch = DocumentProcessingOrchestrator(db)
    _run(orch.run_job(job.id, worker_id="w1"))
    db.refresh(job)
    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert job.progress_percent == 100
    attempts = svc.list_attempts(job.id)
    assert len(attempts) >= 4


def test_noop_permanent_fails(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        metadata={"noop_mode": "permanent"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w1", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w1"))
    db.refresh(job)
    assert job.status == ProcessingJobStatus.FAILED.value
    assert job.last_error_code == "noop_permanent"


def test_noop_retryable_schedules_retry(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        metadata={"noop_mode": "retryable"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w1", batch_size=1, lease_seconds=60)
    policy = ProcessingRetryPolicy(max_attempts=3, initial_delay_seconds=1, max_delay_seconds=10, jitter=False)
    _run(DocumentProcessingOrchestrator(db, retry_policy=policy).run_job(job.id, worker_id="w1"))
    db.refresh(job)
    assert job.status == ProcessingJobStatus.RETRYING.value
    steps = {s.step_key: s for s in svc.list_steps(job.id)}
    noop = steps["noop_processing"]
    assert noop.status == ProcessingStepStatus.RETRYING.value
    assert noop.next_retry_at is not None


def test_cancel_queued(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(organization_id=org.id, document_id=doc.id)
    out = svc.request_cancel(job.id, org.id, actor_user_id=user.id)
    assert out.status == ProcessingJobStatus.CANCELLED.value
    # idempotent
    out2 = svc.request_cancel(job.id, org.id)
    assert out2.status == ProcessingJobStatus.CANCELLED.value


def test_manual_retry_after_fail(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        metadata={"noop_mode": "permanent"},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w1", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w1"))
    db.refresh(job)
    assert job.status == ProcessingJobStatus.FAILED.value
    # clear noop mode then retry
    job.metadata_json = {"noop_mode": "ok"}
    db.commit()
    retried = svc.request_retry(job.id, org.id, actor_user_id=user.id)
    assert retried.status == ProcessingJobStatus.QUEUED.value
    DocumentProcessingRepository(db).claim_jobs(worker_id="w2", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w2"))
    db.refresh(job)
    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert len(svc.list_attempts(job.id)) > 4


def test_job_global_timeout(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(organization_id=org.id, document_id=doc.id)
    job.timeout_at = datetime.utcnow() - timedelta(seconds=1)
    db.commit()
    DocumentProcessingRepository(db).claim_jobs(worker_id="w1", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w1"))
    db.refresh(job)
    assert job.status in (
        ProcessingJobStatus.TIMED_OUT.value,
        ProcessingJobStatus.FAILED.value,
    )


def test_version_pinned_during_job(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    v1 = doc.current_version_id
    from app.storage.document_version_service import DocumentVersionService
    from tests.document_processing.conftest_helpers import registry_svc

    reg = registry_svc(db, tmp_path)
    DocumentVersionService(db, storage=reg.storage).add_version_from_chunks_sync(
        document_id=doc.id,
        organization_id=org.id,
        filename="v2.txt",
        chunks=[b"version-2"],
        declared_mime="text/plain",
        created_by_user_id=user.id,
        change_reason="replace",
    )
    db.refresh(doc)
    assert doc.current_version_id != v1
    svc = DocumentProcessingService(db)
    job = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        document_version_id=v1,
    )
    assert job.document_version_id == v1
    DocumentProcessingRepository(db).claim_jobs(worker_id="w1", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w1"))
    db.refresh(job)
    assert job.status == ProcessingJobStatus.COMPLETED.value
    assert job.document_version_id == v1
