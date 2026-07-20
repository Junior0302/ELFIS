"""Tests JobWorker — claim, exécution, retry, dead letter."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.jobs import job_models  # noqa: F401
from app.jobs.handlers.health_handlers import HealthCheckJobHandler
from app.jobs.handlers.vault_handlers import VaultDocumentMetadataCheckHandler
from app.jobs.job_models import ElfisJob, ElfisJobAttempt
from app.jobs.job_registry import JobHandlerRegistry
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import AttemptStatus, JobNames, JobStatus
from app.jobs.job_worker import JobWorker, compute_job_retry_delay_seconds
from app.models_vault import VaultDocument  # noqa: F401
from app import models_saas  # noqa: F401


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _session(engine=None):
    eng = engine or _engine()
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)(), eng


def _registry():
    reg = JobHandlerRegistry()
    reg.register(job_name=JobNames.SYSTEM_HEALTH_CHECK, handler=HealthCheckJobHandler())
    reg.register(
        job_name=JobNames.VAULT_DOCUMENT_METADATA_CHECK,
        handler=VaultDocumentMetadataCheckHandler(),
    )
    return reg


def test_backoff_sequence():
    assert compute_job_retry_delay_seconds(1, base_seconds=15, jitter=False) == 15
    assert compute_job_retry_delay_seconds(2, base_seconds=15, jitter=False) == 45
    assert compute_job_retry_delay_seconds(3, base_seconds=15, jitter=False) == 135
    assert compute_job_retry_delay_seconds(4, base_seconds=15, jitter=False) == 405
    assert compute_job_retry_delay_seconds(5, base_seconds=15, jitter=False) == 1215
    assert compute_job_retry_delay_seconds(10, base_seconds=15, jitter=False) == 3600
    d = compute_job_retry_delay_seconds(2, base_seconds=15, jitter=True, jitter_seed=1.0)
    assert d == 45


def test_worker_reserves_executes_completes_with_attempt():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, payload={"message": "x"}))
    worker = JobWorker(db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)())
    n = worker.process_next_batch()
    assert n == 1
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.result["ok"] is True
    assert job.result["echo"] == "x"
    attempts = db.query(ElfisJobAttempt).filter(ElfisJobAttempt.job_id == r.job_id).all()
    assert len(attempts) == 1
    assert attempts[0].status == AttemptStatus.COMPLETED


def test_progress_updated():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            payload={"simulate": "progress", "message": "p"},
        )
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100


def test_retryable_schedules_retry():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            payload={"simulate": "retry"},
            max_attempts=5,
        )
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.RETRY
    assert job.attempt_count == 1
    assert job.available_at > datetime.utcnow()
    assert job.last_error
    assert "api_key" not in (job.last_error or "").lower() or "***" in (job.last_error or "")
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.JOB_RETRY_SCHEDULED)
        .count()
    )
    assert events >= 1


def test_permanent_error_no_loop():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            payload={"simulate": "permanent"},
            max_attempts=5,
        )
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.FAILED
    assert job.attempt_count == 1


def test_max_attempts_dead_letter():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            payload={"simulate": "retry"},
            max_attempts=1,
        )
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.DEAD_LETTER
    assert (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.JOB_DEAD_LETTERED)
        .count()
        >= 1
    )


def test_completed_not_replayed():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK))
    w = JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    )
    w.process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.COMPLETED
    # Remettre en pending artificiellement ne doit pas se faire via worker sur completed
    w.process_job(r.job_id)
    job2 = svc.get_job(r.job_id)
    assert job2.status == JobStatus.COMPLETED
    assert db.query(ElfisJobAttempt).filter(ElfisJobAttempt.job_id == r.job_id).count() == 1


def test_expired_lock_recovered():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK))
    job = svc.get_job(r.job_id)
    job.status = JobStatus.PROCESSING
    job.locked_at = datetime.utcnow() - timedelta(hours=1)
    job.heartbeat_at = datetime.utcnow() - timedelta(hours=1)
    job.locked_by = "dead-worker"
    job.attempt_count = 1
    db.commit()
    db.add(
        ElfisJobAttempt(
            id="a1",
            job_id=job.job_id,
            attempt_number=1,
            worker_id="dead-worker",
            status=AttemptStatus.PROCESSING,
            started_at=datetime.utcnow() - timedelta(hours=1),
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
    )
    db.commit()
    JobWorker(
        db,
        registry=reg,
        worker_id="w2",
        lock_timeout_seconds=60,
        session_factory=lambda: sessionmaker(bind=eng)(),
    ).process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.attempt_count == 2
    assert db.query(ElfisJobAttempt).filter(ElfisJobAttempt.job_id == r.job_id).count() == 2


def test_two_workers_do_not_double_claim():
    eng = _engine()
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)
    db1 = Session()
    db2 = Session()
    reg = _registry()
    r = JobService(db1, registry=reg).enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK)
    )
    db1.commit()
    w1 = JobWorker(db1, registry=reg, worker_id="wa", batch_size=10)
    w2 = JobWorker(db2, registry=reg, worker_id="wb", batch_size=10)
    c1 = w1.reserve_next_batch()
    c2 = w2.reserve_next_batch()
    ids = {j.job_id for j in c1} | {j.job_id for j in c2}
    assert r.job_id in ids
    assert len(c1) + len(c2) == 1


def test_queue_selection():
    db, eng = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    r_default = svc.enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, queue_name="default")
    )
    r_ocr = svc.enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, queue_name="ocr")
    )
    claimed = JobWorker(
        db, registry=reg, worker_id="w1", queues=["ocr"]
    ).reserve_next_batch()
    assert len(claimed) == 1
    assert claimed[0].job_id == r_ocr.job_id
    assert claimed[0].job_id != r_default.job_id


def test_priority_order():
    db, _ = _session()
    reg = _registry()
    svc = JobService(db, registry=reg)
    low = svc.enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, priority=50, payload={"m": "urgent"})
    )
    high = svc.enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, priority=200, payload={"m": "later"})
    )
    claimed = JobWorker(db, registry=reg, worker_id="w1", batch_size=1).reserve_next_batch()
    assert len(claimed) == 1
    assert claimed[0].job_id == low.job_id
    assert claimed[0].job_id != high.job_id


def test_scheduled_not_run_early():
    db, _ = _session()
    reg = _registry()
    future = datetime.utcnow() + timedelta(hours=2)
    JobService(db, registry=reg).enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, scheduled_at=future)
    )
    claimed = JobWorker(db, registry=reg, worker_id="w1").reserve_next_batch()
    assert claimed == []


def test_health_check_success_and_started_completed_events():
    db, eng = _session()
    reg = _registry()
    r = JobService(db, registry=reg).enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, organization_id=1)
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.JOB_STARTED in names
    assert EventNames.JOB_COMPLETED in names
    job = JobService(db, registry=reg).get_job(r.job_id)
    assert job.result["ok"] is True


def test_metadata_check_success_and_missing():
    db, eng = _session()
    # tables org/users via models
    from app.models_saas import Organization, User

    org = Organization(id=1, name="T")
    user = User(
        id=1,
        email="a@b.c",
        first_name="A",
        last_name="B",
        password_hash="x",
    )
    db.add(org)
    db.add(user)
    db.flush()
    doc = VaultDocument(
        id="doc-1",
        organization_id=1,
        document_type="customer_invoice",
        original_filename="f.pdf",
        storage_path="org/1/f.pdf",
        mime_type="application/pdf",
        file_size=1234,
        checksum_sha256="abc",
        archive_status="archived",
    )
    db.add(doc)
    db.commit()

    reg = _registry()
    svc = JobService(db, registry=reg)
    r = svc.enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_METADATA_CHECK,
            organization_id=1,
            payload={
                "vault_document_id": "doc-1",
                "expected_document_type": "customer_invoice",
            },
        )
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    job = svc.get_job(r.job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.result["valid"] is True

    r2 = svc.enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_METADATA_CHECK,
            organization_id=1,
            payload={"vault_document_id": "missing"},
        )
    )
    JobWorker(
        db, registry=reg, worker_id="w1", session_factory=lambda: sessionmaker(bind=eng)()
    ).process_next_batch()
    job2 = svc.get_job(r2.job_id)
    assert job2.status == JobStatus.FAILED
