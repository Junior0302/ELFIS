"""Helpers tests extraction."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit import audit_models  # noqa: F401
from app.config import settings
from app.database import Base
from app.document_processing import models as dp_models  # noqa: F401
from app.document_processing.classification import models as cls_models  # noqa: F401
from app.document_processing.extraction import models as extr_models  # noqa: F401
from app.document_processing.extraction.provider_registry import reset_extraction_provider_registry_for_tests
from app.document_processing.extraction.schema_registry import reset_extraction_schema_registry_for_tests
from app.document_processing.ocr import models as ocr_models  # noqa: F401
from app.document_processing.ocr.provider_registry import reset_ocr_provider_registry_for_tests
from app.document_processing.orchestrator import DocumentProcessingOrchestrator
from app.document_processing.repository import DocumentProcessingRepository
from app.document_processing.service import DocumentProcessingService
from app.document_processing.step_registry import reset_pipeline_registry_for_tests
from app.document_processing.types import PIPELINE_OCR_V1
from app.models_saas import Organization, User  # noqa: F401
from app.storage import storage_models  # noqa: F401
from app.storage.document_registry_service import DocumentRegistryService
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext


def make_extraction_db():
    reset_pipeline_registry_for_tests()
    reset_ocr_provider_registry_for_tests()
    reset_extraction_provider_registry_for_tests()
    reset_extraction_schema_registry_for_tests()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Organization.__table__,
            storage_models.ElfisStorageObject.__table__,
            storage_models.ElfisDocumentRecord.__table__,
            storage_models.ElfisDocumentLink.__table__,
            storage_models.ElfisDocumentVersion.__table__,
            storage_models.ElfisDocumentLegalHold.__table__,
            storage_models.ElfisDocumentTombstone.__table__,
            audit_models.ElfisAuditEvent.__table__,
            dp_models.ElfisDocumentProcessingJob.__table__,
            dp_models.ElfisDocumentProcessingStep.__table__,
            dp_models.ElfisDocumentProcessingAttempt.__table__,
            cls_models.ElfisDocumentClassification.__table__,
            ocr_models.ElfisDocumentOCRResult.__table__,
            ocr_models.ElfisDocumentOCRPage.__table__,
            extr_models.ElfisDocumentExtractionResult.__table__,
            extr_models.ElfisDocumentExtractedField.__table__,
            extr_models.ElfisDocumentExtractionReview.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session, engine


def seed_org_user(db):
    org = Organization(name="Org Extr")
    db.add(org)
    db.flush()
    user = User(
        first_name="E",
        last_name="X",
        email="extr@test.local",
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user


def seed_document(db, tmp_path: Path, org, user, *, filename="a.pdf", content=b"%PDF-1.4\n%%EOF"):
    svc = DocumentRegistryService(
        db,
        context=StorageContext(provider=LocalStorageProvider(root=tmp_path), namespace="test"),
    )
    return svc.create_from_upload(
        organization_id=org.id,
        filename=filename,
        content=content,
        declared_mime="application/pdf",
        owner_user_id=user.id,
        title=filename,
    )


def run_ocr_noop(db, doc, *, monkeypatch=None):
    if monkeypatch:
        monkeypatch.setattr(settings, "document_ocr_enabled", True)
        monkeypatch.setattr(settings, "document_ocr_provider", "noop")
    job = DocumentProcessingService(db).create_job(
        organization_id=doc.organization_id,
        document_id=doc.id,
        document_version_id=doc.current_version_id,
        pipeline_key=PIPELINE_OCR_V1,
        idempotency_key=f"ocr-{doc.id}",
        metadata={"force_ocr_enabled": True, "noop_mode": "ok", "noop_pages": 1},
    )
    DocumentProcessingRepository(db).claim_jobs(worker_id="t", batch_size=1, lease_seconds=60)
    asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="t"))
    db.refresh(job)
    return job
