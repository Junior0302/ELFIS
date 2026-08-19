"""RC2.5.8 — Concurrence Document Processing sur PostgreSQL réel.

Cas A (claim), B (lease recovery), C (retry concurrent).
Jamais SQLite. Skip uniquement si garde-fous PG absents.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete

from app.document_processing import metrics as dp_metrics
from app.document_processing.models import ElfisDocumentProcessingJob
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.types import ProcessingJobStatus
from app.jobs.job_models import ElfisJob, ElfisJobAttempt
from app.jobs.job_repository import JobRepository
from app.jobs.job_types import JobNames, JobStatus
from app.models_saas import Organization
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres

PIPELINE = f"rc258_probe_pipeline_{uuid4().hex[:8]}"
JOIN_TIMEOUT = 45


def _cleanup_rc1_queue(db, *, job_ids: list[str] | None = None) -> None:
    q = db.query(ElfisJob).filter(ElfisJob.queue_name == "rc1")
    if job_ids is not None:
        q = q.filter(ElfisJob.job_id.in_(job_ids))
    targets = [row.job_id for row in q.all()]
    if not targets:
        return
    db.execute(delete(ElfisJobAttempt).where(ElfisJobAttempt.job_id.in_(targets)))
    db.execute(
        delete(ElfisJob).where(
            ElfisJob.queue_name == "rc1",
            ElfisJob.job_id.in_(targets),
        )
    )
    db.commit()


def _seed_org(db) -> int:
    org = Organization(name=f"rc258-dp-{uuid4().hex[:8]}")
    db.add(org)
    db.flush()
    return int(org.id)


def _make_job(
    *,
    org_id: int,
    status: str = ProcessingJobStatus.QUEUED.value,
    scheduled_at: datetime | None = None,
    locked_by: str | None = None,
    locked_until: datetime | None = None,
    pipeline_key: str = PIPELINE,
) -> ElfisDocumentProcessingJob:
    now = datetime.utcnow()
    return ElfisDocumentProcessingJob(
        id=str(uuid4()),
        document_id=str(uuid4()),
        document_version_id=str(uuid4()),
        organization_id=org_id,
        pipeline_key=pipeline_key,
        status=status,
        priority=50,
        scheduled_at=scheduled_at or now,
        locked_by=locked_by,
        locked_until=locked_until,
        locked_at=now if locked_by else None,
        heartbeat_at=now if locked_by else None,
        metadata_json={"probe": "rc258"},
    )


def test_postgres_job_claiming_skip_locked_unique():
    """RC1 ElfisJob — 100 jobs, 4 workers — chaque job claimé une seule fois."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    import inspect
    from app.jobs.job_repository import JobRepository as JR

    src = inspect.getsource(JR._claim_jobs_postgres)
    assert "FOR UPDATE SKIP LOCKED" in src

    db = Session()
    try:
        _cleanup_rc1_queue(db)
    finally:
        db.close()

    db = Session()
    now = datetime.utcnow()
    prefix = f"rc1-job-{uuid4().hex[:8]}"
    job_ids: list[str] = []
    try:
        for i in range(100):
            jid = str(uuid4())
            job_ids.append(jid)
            db.add(
                ElfisJob(
                    id=str(uuid4()),
                    job_id=jid,
                    job_name=JobNames.SYSTEM_HEALTH_CHECK,
                    status=JobStatus.PENDING,
                    payload={"rc1": prefix, "i": i},
                    queue_name="rc1",
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()
    finally:
        db.close()

    target = set(job_ids)
    claimed: list[str] = []
    lock = threading.Lock()
    errors: list[str] = []

    def worker(wid: str) -> None:
        local = Session()
        try:
            idle = 0
            while idle < 3:
                batch = JobRepository(local).claim_jobs(
                    worker_id=wid,
                    queues=["rc1"],
                    batch_size=10,
                    lock_timeout_seconds=60,
                )
                ours = [j.job_id for j in batch if j.job_id in target]
                if ours:
                    idle = 0
                    with lock:
                        claimed.extend(ours)
                else:
                    idle += 1
                with lock:
                    if len(set(claimed)) >= 100:
                        break
        except Exception as exc:
            with lock:
                errors.append(f"{wid}:{type(exc).__name__}")
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(f"rc1-w-{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors, errors
    processed_ids = set(claimed)
    assert len(processed_ids) == 100
    assert processed_ids == target

    db = Session()
    try:
        _cleanup_rc1_queue(db, job_ids=job_ids)
    finally:
        db.close()


def test_A_processing_claim_concurrent_unique():
    """A — deux+ sessions PG : un seul claim gagnant par job (SKIP LOCKED)."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    import inspect

    src = inspect.getsource(DocumentProcessingRepository._claim_postgres)
    assert "FOR UPDATE SKIP LOCKED" in src

    db = Session()
    org_id = None
    job_ids: list[str] = []
    try:
        org_id = _seed_org(db)
        for _ in range(12):
            job = _make_job(org_id=org_id)
            db.add(job)
            job_ids.append(job.id)
        db.commit()
    finally:
        db.close()

    barrier = threading.Barrier(4, timeout=JOIN_TIMEOUT)
    claimed: list[tuple[str, str]] = []
    lock = threading.Lock()
    errors: list[str] = []

    def worker(wid: str) -> None:
        local = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            rows = DocumentProcessingRepository(local).claim_jobs(
                worker_id=wid,
                batch_size=5,
                lease_seconds=60,
                pipeline_key=PIPELINE,
            )
            with lock:
                for r in rows:
                    claimed.append((wid, r.id))
                    assert r.locked_by == wid
                    assert r.locked_until is not None
                    assert r.status == ProcessingJobStatus.RUNNING.value
        except Exception as exc:
            with lock:
                errors.append(f"{wid}:{type(exc).__name__}:{exc}")
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(f"dp-a-{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        assert t.join(timeout=JOIN_TIMEOUT) is None or not t.is_alive()

    assert not errors, errors
    ids = [jid for _, jid in claimed if jid in set(job_ids)]
    assert len(ids) == len(set(ids)), "double claim processing détecté"
    assert set(ids) == set(job_ids)
    assert len(ids) == 12

    db = Session()
    try:
        db.query(ElfisDocumentProcessingJob).filter(
            ElfisDocumentProcessingJob.id.in_(job_ids)
        ).delete(synchronize_session=False)
        if org_id:
            db.query(Organization).filter(Organization.id == org_id).delete(
                synchronize_session=False
            )
        db.commit()
    finally:
        db.close()


def test_B_processing_lease_expiry_recovery():
    """B — lease expirée récupérée une seule fois ; métrique leases_recovered."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    dp_metrics.reset_for_tests()
    db = Session()
    org_id = None
    job_id = None
    try:
        org_id = _seed_org(db)
        expired = datetime.utcnow() - timedelta(seconds=120)
        job = _make_job(
            org_id=org_id,
            status=ProcessingJobStatus.RUNNING.value,
            locked_by="dead-worker",
            locked_until=expired,
        )
        job.heartbeat_at = expired
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    barrier = threading.Barrier(3, timeout=JOIN_TIMEOUT)
    winners: list[str] = []
    lock = threading.Lock()

    def worker(wid: str) -> None:
        local = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            rows = DocumentProcessingRepository(local).claim_jobs(
                worker_id=wid,
                batch_size=5,
                lease_seconds=30,
                pipeline_key=PIPELINE,
            )
            with lock:
                for r in rows:
                    if r.id == job_id:
                        winners.append(wid)
                        assert getattr(r, "_lease_recovered", False) is True
                        assert r.locked_by == wid
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(f"dp-b-{i}",)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT)

    assert len(winners) == 1, winners
    assert dp_metrics.snapshot().get("leases_recovered", 0) >= 1

    db = Session()
    try:
        if job_id:
            db.query(ElfisDocumentProcessingJob).filter(
                ElfisDocumentProcessingJob.id == job_id
            ).delete(synchronize_session=False)
        if org_id:
            db.query(Organization).filter(Organization.id == org_id).delete(
                synchronize_session=False
            )
        db.commit()
    finally:
        db.close()


def test_C_processing_retry_concurrent_unique():
    """C — job retrying claimé par un seul worker concurrent."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    db = Session()
    org_id = None
    job_id = None
    try:
        org_id = _seed_org(db)
        job = _make_job(
            org_id=org_id,
            status=ProcessingJobStatus.RETRYING.value,
            scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        )
        db.add(job)
        db.commit()
        job_id = job.id
    finally:
        db.close()

    barrier = threading.Barrier(4, timeout=JOIN_TIMEOUT)
    claimed_by: list[str] = []
    lock = threading.Lock()

    def worker(wid: str) -> None:
        local = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            rows = DocumentProcessingRepository(local).claim_jobs(
                worker_id=wid,
                batch_size=3,
                lease_seconds=60,
                pipeline_key=PIPELINE,
            )
            with lock:
                for r in rows:
                    if r.id == job_id:
                        claimed_by.append(wid)
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(f"dp-c-{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT)

    assert len(claimed_by) == 1, claimed_by

    db = Session()
    try:
        if job_id:
            db.query(ElfisDocumentProcessingJob).filter(
                ElfisDocumentProcessingJob.id == job_id
            ).delete(synchronize_session=False)
        if org_id:
            db.query(Organization).filter(Organization.id == org_id).delete(
                synchronize_session=False
            )
        db.commit()
    finally:
        db.close()


def test_J_processing_api_org_isolation_list():
    """J — list_jobs filtrée par organization_id (pas de fuite cross-tenant)."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    db = Session()
    org_a = org_b = None
    job_ids: list[str] = []
    try:
        org_a = _seed_org(db)
        org_b = _seed_org(db)
        ja = _make_job(org_id=org_a, pipeline_key=f"{PIPELINE}_iso")
        jb = _make_job(org_id=org_b, pipeline_key=f"{PIPELINE}_iso")
        db.add(ja)
        db.add(jb)
        db.commit()
        job_ids = [ja.id, jb.id]
        repo = DocumentProcessingRepository(db)
        items_a, _ = repo.list_jobs(organization_id=org_a, limit=50, offset=0)
        ids_a = {j.id for j in items_a}
        assert ja.id in ids_a
        assert jb.id not in ids_a
    finally:
        if job_ids:
            db.query(ElfisDocumentProcessingJob).filter(
                ElfisDocumentProcessingJob.id.in_(job_ids)
            ).delete(synchronize_session=False)
        for oid in (org_a, org_b):
            if oid:
                db.query(Organization).filter(Organization.id == oid).delete(
                    synchronize_session=False
                )
        db.commit()
        db.close()
