"""Tests pipeline classification + revue + idempotence."""

from __future__ import annotations

import asyncio

from app.document_processing.classification.service import DocumentClassificationService
from app.document_processing.orchestrator import DocumentProcessingOrchestrator
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.service import DocumentProcessingService
from app.document_processing.types import PIPELINE_BASIC_V1, PIPELINE_CLASSIFICATION_V1
from tests.document_classification.conftest_helpers import make_classification_db, seed_document, seed_org_user


def _run(c):
    return asyncio.run(c)


def test_classification_pipeline_persists(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user, filename="facture.pdf", content=b"%PDF-1.4")
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        pipeline_key=PIPELINE_CLASSIFICATION_V1,
    )
    assert len(DocumentProcessingService(db).list_steps(job.id)) == 5
    DocumentProcessingRepository(db).claim_jobs(worker_id="w", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w"))
    db.refresh(job)
    assert job.status == "completed"
    items, total = DocumentClassificationService(db).list_classifications(
        organization_id=org.id, document_id=doc.id
    )
    assert total >= 1
    row = items[0]
    assert row.document_version_id == doc.current_version_id
    assert row.predicted_type in ("invoice", "supporting_document", "unknown")
    assert row.confidence_score >= 0
    assert isinstance(row.evidence_json, list)
    # pas de filename dans evidence
    assert all("@" not in str(e) for e in (row.evidence_json or []))


def test_idempotent_persist(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user, filename="devis.pdf", content=b"%PDF")
    svc = DocumentClassificationService(db)
    from app.storage.storage_models import ElfisDocumentVersion, ElfisStorageObject

    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    obj = db.get(ElfisStorageObject, ver.storage_object_id)
    result = _run(svc.run_classifier(document=doc, version=ver, storage_object=obj))
    a = svc.persist_result(document=doc, version=ver, result=result, job_id=None)
    b = svc.persist_result(document=doc, version=ver, result=result, job_id=None)
    assert a.id == b.id


def test_confirm_reject_reclassify(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user, filename="devis.pdf", content=b"%PDF")
    svc = DocumentClassificationService(db)
    from app.storage.storage_models import ElfisDocumentVersion, ElfisStorageObject

    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    obj = db.get(ElfisStorageObject, ver.storage_object_id)
    result = _run(svc.run_classifier(document=doc, version=ver, storage_object=obj))
    row = svc.persist_result(document=doc, version=ver, result=result)
    confirmed = svc.confirm(row.id, org.id, confirmed_type="quote", actor_user_id=user.id)
    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_type == "quote"
    assert confirmed.predicted_type == row.predicted_type  # immuable
    db.refresh(doc)
    assert doc.document_type == "quote"

    # reject autre
    doc2 = seed_document(db, tmp_path, org, user, filename="x.pdf", content=b"%PDF2")
    ver2 = db.get(ElfisDocumentVersion, doc2.current_version_id)
    obj2 = db.get(ElfisStorageObject, ver2.storage_object_id)
    r2 = _run(svc.run_classifier(document=doc2, version=ver2, storage_object=obj2))
    row2 = svc.persist_result(document=doc2, version=ver2, result=r2, force=True)
    rejected = svc.reject(row2.id, org.id, reason="mauvais type")
    assert rejected.status == "rejected"

    job = svc.request_reclassify(confirmed.id, org.id, actor_user_id=user.id, force=True)
    assert job.pipeline_key == PIPELINE_CLASSIFICATION_V1
    assert job.document_version_id == doc.current_version_id


def test_cross_tenant_denied(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    org2 = type(org)(name="Other")
    db.add(org2)
    db.commit()
    db.refresh(org2)
    doc = seed_document(db, tmp_path, org, user, filename="devis.pdf", content=b"%PDF")
    svc = DocumentClassificationService(db)
    from app.storage.storage_models import ElfisDocumentVersion, ElfisStorageObject

    ver = db.get(ElfisDocumentVersion, doc.current_version_id)
    obj = db.get(ElfisStorageObject, ver.storage_object_id)
    result = _run(svc.run_classifier(document=doc, version=ver, storage_object=obj))
    row = svc.persist_result(document=doc, version=ver, result=result)
    import pytest
    from app.document_processing.classification.exceptions import ClassificationAccessDeniedError

    with pytest.raises(ClassificationAccessDeniedError):
        svc.get_for_org(row.id, org2.id)


def test_basic_pipeline_still_works(tmp_path):
    factory, _ = make_classification_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user, filename="a.txt", content=b"hello")
    job = DocumentProcessingService(db).create_job(
        organization_id=org.id,
        document_id=doc.id,
        pipeline_key=PIPELINE_BASIC_V1,
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="w", batch_size=1, lease_seconds=60)
    _run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="w"))
    db.refresh(job)
    assert job.status == "completed"
