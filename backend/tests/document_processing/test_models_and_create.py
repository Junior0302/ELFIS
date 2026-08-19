"""Tests modèles / création job / idempotence."""

from __future__ import annotations

import pytest

from app.document_processing.exceptions import ProcessingValidationError
from app.document_processing.service import DocumentProcessingService
from app.document_processing.types import ProcessingJobStatus, ProcessingStepStatus
from tests.document_processing.conftest_helpers import make_processing_db, seed_document, seed_org_user


def test_create_job_with_steps(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        requested_by_user_id=user.id,
    )
    assert job.status == ProcessingJobStatus.QUEUED.value
    assert job.document_version_id == doc.current_version_id
    assert 0 <= job.progress_percent <= 100
    steps = svc.list_steps(job.id)
    assert len(steps) == 4
    assert steps[0].status == ProcessingStepStatus.READY.value
    assert steps[0].sequence_number == 1
    assert {s.sequence_number for s in steps} == {1, 2, 3, 4}


def test_idempotency_returns_same_job(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    a = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        idempotency_key="idem-1",
    )
    b = svc.create_job(
        organization_id=org.id,
        document_id=doc.id,
        idempotency_key="idem-1",
    )
    assert a.id == b.id
    assert len(svc.list_steps(a.id)) == 4


def test_unknown_pipeline(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    with pytest.raises(ProcessingValidationError) as exc:
        svc.create_job(
            organization_id=org.id,
            document_id=doc.id,
            pipeline_key="unknown_pipeline",
        )
    assert exc.value.code == "pipeline_unknown"


def test_cross_tenant_get_denied(tmp_path):
    factory, _ = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    org2 = type(org)(name="Other")
    db.add(org2)
    db.commit()
    db.refresh(org2)
    doc = seed_document(db, tmp_path, org, user)
    svc = DocumentProcessingService(db)
    job = svc.create_job(organization_id=org.id, document_id=doc.id)
    with pytest.raises(Exception):
        svc.get_job_for_org(job.id, org2.id)
