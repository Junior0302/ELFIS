"""Probe staging RC2.5.4 — extraction structurée (noop/rules). Aucune IA."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="noop", choices=["noop", "rules"])
    parser.add_argument("--apply-sql", action="store_true")
    parser.add_argument("--keep-probes", action="store_true")
    args = parser.parse_args()

    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip()
    if not env:
        raise SystemExit("FATAL: ELFIS_ENVIRONMENT requis")
    print(f"ELFIS_ENVIRONMENT={env} provider={args.provider}")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.audit import audit_models  # noqa: F401
    from app.config import settings
    from app.database import Base
    from app.document_processing import models as dp_models  # noqa: F401
    from app.document_processing.classification import models as cls_models  # noqa: F401
    from app.document_processing.extraction import models as extr_models  # noqa: F401
    from app.document_processing.extraction.provider_registry import (
        reset_extraction_provider_registry_for_tests,
    )
    from app.document_processing.extraction.schema_registry import (
        reset_extraction_schema_registry_for_tests,
    )
    from app.document_processing.extraction.service import DocumentExtractionService
    from app.document_processing.extraction.types import PIPELINE_EXTRACTION_V1
    from app.document_processing.ocr import models as ocr_models  # noqa: F401
    from app.document_processing.ocr.provider_registry import reset_ocr_provider_registry_for_tests
    from app.document_processing.orchestrator import DocumentProcessingOrchestrator
    from app.document_processing.repository import DocumentProcessingRepository
    from app.document_processing.service import DocumentProcessingService
    from app.document_processing.step_registry import reset_pipeline_registry_for_tests
    from app.document_processing.types import PIPELINE_OCR_V1
    from app.models_saas import Organization, User
    from app.storage import storage_models  # noqa: F401
    from app.storage.document_registry_service import DocumentRegistryService
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_context import StorageContext

    reset_pipeline_registry_for_tests()
    reset_ocr_provider_registry_for_tests()
    reset_extraction_provider_registry_for_tests()
    reset_extraction_schema_registry_for_tests()

    settings.document_ocr_enabled = True
    settings.document_ocr_provider = "noop"
    settings.document_extraction_enabled = True
    settings.document_extraction_provider = args.provider

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    org = Organization(name="Extr Probe")
    db.add(org)
    db.flush()
    user = User(
        first_name="P",
        last_name="E",
        email=f"extr-{uuid4().hex[:8]}@example.invalid",
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()

    keep = args.keep_probes
    tmp_ctx = tempfile.TemporaryDirectory()
    tmp = Path(tmp_ctx.name)
    try:
        root = tmp / "obj"
        root.mkdir()
        reg = DocumentRegistryService(
            db,
            context=StorageContext(provider=LocalStorageProvider(root=root), namespace="probe"),
        )
        doc = reg.create_from_upload(
            organization_id=org.id,
            filename="extr-probe.pdf",
            content=b"%PDF-1.4 probe\n%%EOF",
            declared_mime="application/pdf",
            owner_user_id=user.id,
            title="extr-probe",
        )
        print("OK probe document")

        svc_job = DocumentProcessingService(db)
        # OCR d'abord
        job_o = svc_job.create_job(
            organization_id=org.id,
            document_id=doc.id,
            document_version_id=doc.current_version_id,
            pipeline_key=PIPELINE_OCR_V1,
            idempotency_key=f"stage4-ocr-{doc.id}",
            metadata={"force_ocr_enabled": True, "noop_mode": "ok", "noop_pages": 1},
        )
        DocumentProcessingRepository(db).claim_jobs(worker_id="stage4", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job_o.id, worker_id="stage4"))
        db.refresh(job_o)
        assert job_o.status == "completed", job_o.status
        print("OK OCR probe")

        meta = {"force_extraction_enabled": True, "noop_mode": "ok"}
        if args.provider == "rules":
            meta = {"force_extraction_enabled": True}
        job = svc_job.create_job(
            organization_id=org.id,
            document_id=doc.id,
            document_version_id=doc.current_version_id,
            pipeline_key=PIPELINE_EXTRACTION_V1,
            idempotency_key=f"stage4-extr-{doc.id}",
            metadata=meta,
        )
        DocumentProcessingRepository(db).claim_jobs(worker_id="stage4", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="stage4"))
        db.refresh(job)
        assert job.status == "completed", (job.status, job.error_code)
        print("OK extraction job")

        extr = DocumentExtractionService(db)
        items, total = extr.list_results(organization_id=org.id, document_id=doc.id)
        assert total >= 1
        row = items[0]
        assert row.document_version_id == doc.current_version_id
        print(
            f"OK result schema={row.schema_key} provider={row.provider_key} "
            f"status={row.status} fields={row.fields_count}"
        )
        data, _ = extr.open_content(row.id, org.id, actor_user_id=user.id)
        assert data
        confirmed = extr.confirm(row.id, org.id, actor_user_id=user.id)
        assert confirmed.status == "confirmed"
        print("OK confirm")
        print("PASS stage4 extraction probes")
        return 0
    finally:
        db.close()
        if not keep:
            tmp_ctx.cleanup()
        else:
            print(f"KEEP {tmp}")


if __name__ == "__main__":
    raise SystemExit(main())
