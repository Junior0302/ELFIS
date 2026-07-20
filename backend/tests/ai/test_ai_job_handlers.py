"""Tests handlers Job Queue AI."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models, bootstrap_ai_tasks  # noqa: F401
from app.database import Base
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.job_worker import JobWorker
from app.models_saas import Organization, User
from app.models_vault import VaultDocument
from app.ai.ai_models import ElfisDocumentAnalysis
from app.ai.ai_types import DocumentAnalysisStatus
import uuid
from datetime import datetime


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Org"))
    db.add(
        User(id=1, email="a@b.c", first_name="A", last_name="B", password_hash="x")
    )
    db.add(
        VaultDocument(
            id="vd-1",
            organization_id=1,
            document_type="supplier_invoice",
            original_filename="f.pdf",
            storage_path="p",
            mime_type="application/pdf",
            file_size=100,
            checksum_sha256="abc",
            archive_status="archived",
            version=1,
        )
    )
    db.commit()
    bootstrap_ai_tasks()
    bootstrap_job_handlers()
    return db, Session, engine


def test_classification_extraction_quality_jobs():
    db, Session, eng = _setup()
    analysis = ElfisDocumentAnalysis(
        id=str(uuid.uuid4()),
        analysis_id=str(uuid.uuid4()),
        organization_id=1,
        vault_document_id="vd-1",
        document_version=1,
        status=DocumentAnalysisStatus.CLASSIFYING,
        current_stage="classification",
        ai_execution_ids=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(analysis)
    db.commit()

    text = (
        "Facture FAC-100 Société Demo Montant HT 100,00 TVA 20,00 TTC 120,00 "
        "taux 20% date 01/01/2024"
    )
    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION,
            organization_id=1,
            user_id=1,
            payload={
                "vault_document_id": "vd-1",
                "analysis_id": analysis.analysis_id,
                "extracted_text": text,
                "filename": "f.pdf",
                "mime_type": "application/pdf",
                "document_version": 1,
            },
            idempotency_key="t-classify-1",
        )
    )

    factory = lambda: Session()
    worker = JobWorker(db, worker_id="w-ai", session_factory=factory)
    # Traite classification puis jobs enfants
    for _ in range(5):
        n = worker.process_next_batch()
        if n == 0:
            break

    db.refresh(analysis)
    assert analysis.classification is not None
    # extraction et/ou quality selon type détecté
    assert analysis.status in (
        DocumentAnalysisStatus.COMPLETED,
        DocumentAnalysisStatus.REQUIRES_REVIEW,
        DocumentAnalysisStatus.VALIDATING,
        DocumentAnalysisStatus.EXTRACTING,
        DocumentAnalysisStatus.BLOCKED,
    )
    jobs = db.query(job_models.ElfisJob).all()
    assert any(j.job_name == JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION for j in jobs)
    assert any(j.status == JobStatus.COMPLETED for j in jobs)


def test_progress_updated_on_ai_job():
    db, Session, eng = _setup()
    JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.VAULT_DOCUMENT_QUALITY_CHECK,
            organization_id=1,
            payload={
                "vault_document_id": "vd-1",
                "extraction": {
                    "supplier": "A",
                    "invoice_date": "01-01-2024",
                    "invoice_number": "1",
                    "amount_ht": 10.0,
                    "amount_tva": 2.0,
                    "amount_ttc": 12.0,
                    "vat_rate": 20.0,
                    "document_type": "facture",
                    "confidence_score": 0.9,
                },
                "document_version": 1,
            },
        )
    )
    JobWorker(db, worker_id="w2", session_factory=lambda: Session()).process_next_batch()
    job = db.query(job_models.ElfisJob).one()
    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100
