"""Tests queue / lease / double claim."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.service import DocumentProcessingService
from app.document_processing.types import ProcessingJobStatus
from tests.document_processing.conftest_helpers import make_processing_db, seed_document, seed_org_user


def test_two_workers_no_double_claim(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    for i in range(3):
        svc.create_job(organization_id=org.id, document_id=doc.id, idempotency_key=f"k-{i}")

    s1, s2 = factory(), factory()
    a = DocumentProcessingRepository(s1).claim_jobs(worker_id="wa", batch_size=10, lease_seconds=60)
    b = DocumentProcessingRepository(s2).claim_jobs(worker_id="wb", batch_size=10, lease_seconds=60)
    ids_a = {j.id for j in a}
    ids_b = {j.id for j in b}
    assert ids_a.isdisjoint(ids_b)
    assert len(ids_a) + len(ids_b) == 3
    s1.close()
    s2.close()


def test_expired_lease_reclaim(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    job = DocumentProcessingService(db).create_job(organization_id=org.id, document_id=doc.id)
    repo = DocumentProcessingRepository(db)
    claimed = repo.claim_jobs(worker_id="w-dead", batch_size=1, lease_seconds=60)
    assert claimed[0].id == job.id
    job.locked_until = datetime.utcnow() - timedelta(seconds=5)
    job.heartbeat_at = datetime.utcnow() - timedelta(seconds=120)
    db.commit()

    reclaimed = repo.claim_jobs(worker_id="w-alive", batch_size=1, lease_seconds=60)
    assert len(reclaimed) == 1
    assert reclaimed[0].id == job.id
    assert reclaimed[0].locked_by == "w-alive"
    assert reclaimed[0].status == ProcessingJobStatus.RUNNING.value
