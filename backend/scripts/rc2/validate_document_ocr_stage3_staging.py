"""Probe staging RC2.5.3 — OCR framework (noop / native_pdf). Aucun document utilisateur, aucune IA."""

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


def _make_pdf_with_text() -> bytes:
    # PDF minimal avec texte sélectionnable (pas une image scannée)
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        b"4 0 obj<< /Length 44 >>stream\n"
        b"BT /F1 12 Tf 50 150 Td (Hello ELFIS) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="noop", choices=["noop", "native_pdf", "tesseract"])
    parser.add_argument("--apply-sql", action="store_true")
    parser.add_argument("--keep-probes", action="store_true")
    args = parser.parse_args()

    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip()
    if not env:
        raise SystemExit("FATAL: ELFIS_ENVIRONMENT requis")
    print(f"ELFIS_ENVIRONMENT={env}")
    print(f"provider={args.provider}")

    if args.provider == "tesseract":
        print("SKIP: tesseract non activé dans RC2.5.3 par défaut")
        return 0

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.audit import audit_models  # noqa: F401
    from app.config import settings
    from app.database import Base
    from app.document_processing import models as dp_models  # noqa: F401
    from app.document_processing.classification import models as cls_models  # noqa: F401
    from app.document_processing.ocr import models as ocr_models  # noqa: F401
    from app.document_processing.ocr.provider_registry import reset_ocr_provider_registry_for_tests
    from app.document_processing.ocr.service import DocumentOCRService
    from app.document_processing.orchestrator import DocumentProcessingOrchestrator
    from app.document_processing.repository import DocumentProcessingRepository
    from app.document_processing.service import DocumentProcessingService
    from app.document_processing.step_registry import reset_pipeline_registry_for_tests
    from app.document_processing.types import PIPELINE_BASIC_V1, PIPELINE_OCR_V1
    from app.models_saas import Organization, User
    from app.storage import storage_models  # noqa: F401
    from app.storage.document_registry_service import DocumentRegistryService
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_context import StorageContext
    from app.storage.storage_types import StorageObjectStatus

    reset_pipeline_registry_for_tests()
    reset_ocr_provider_registry_for_tests()

    settings.document_ocr_enabled = True
    settings.document_ocr_provider = args.provider
    settings.document_ocr_native_pdf_text_enabled = True

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    org = Organization(name="OCR Probe")
    db.add(org)
    db.flush()
    user = User(
        first_name="P",
        last_name="O",
        email=f"ocr-{uuid4().hex[:8]}@example.invalid",
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
        content = _make_pdf_with_text() if args.provider == "native_pdf" else b"%PDF-1.4 probe\n%%EOF"
        doc = reg.create_from_upload(
            organization_id=org.id,
            filename="ocr-probe.pdf",
            content=content,
            declared_mime="application/pdf",
            owner_user_id=user.id,
            title="ocr-probe",
        )
        print("OK probe document")

        svc_job = DocumentProcessingService(db)
        ocr_svc = DocumentOCRService(db)

        meta = {"force_ocr_enabled": True, "noop_mode": "ok", "noop_pages": 2}
        if args.provider == "native_pdf":
            meta = {"force_ocr_enabled": True}

        job = svc_job.create_job(
            organization_id=org.id,
            document_id=doc.id,
            document_version_id=doc.current_version_id,
            pipeline_key=PIPELINE_OCR_V1,
            idempotency_key=f"stage3-ocr-{doc.id}",
            metadata=meta,
        )
        DocumentProcessingRepository(db).claim_jobs(worker_id="stage3", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="stage3"))
        db.refresh(job)
        assert job.status == "completed", job.status
        print(f"OK job completed pipeline={PIPELINE_OCR_V1}")

        items, total = ocr_svc.list_results(organization_id=org.id, document_id=doc.id)
        assert total >= 1 and items, "missing ocr result"
        row = items[0]
        assert row.document_version_id == doc.current_version_id
        assert row.provider_key in ("noop", "native_pdf")
        print(
            f"OK result provider={row.provider_key} method={row.extraction_method} "
            f"pages={row.page_count} status={row.status}"
        )
        pages = ocr_svc.list_pages(row.id)
        print(f"OK pages={len(pages)}")

        if row.text_artifact_storage_object_id:
            data, _ = ocr_svc.open_text(row.id, org.id, platform=False, actor_user_id=user.id)
            assert data, "empty artifact"
            assert b"schema_version" in data
            print(f"OK artifact stream bytes={len(data)}")

        # basic pipeline encore OK
        job_b = svc_job.create_job(
            organization_id=org.id,
            document_id=doc.id,
            pipeline_key=PIPELINE_BASIC_V1,
            idempotency_key=f"stage3-basic-{doc.id}",
        )
        DocumentProcessingRepository(db).claim_jobs(worker_id="stage3", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job_b.id, worker_id="stage3"))
        db.refresh(job_b)
        assert job_b.status == "completed"
        print("OK document_basic_v1 non-régression")

        # quarantine bloque
        from app.storage.storage_models import ElfisStorageObject

        sobj = db.get(ElfisStorageObject, doc.current_storage_object_id)
        assert sobj is not None
        sobj.status = StorageObjectStatus.QUARANTINED.value
        db.commit()
        job_q = svc_job.create_job(
            organization_id=org.id,
            document_id=doc.id,
            pipeline_key=PIPELINE_OCR_V1,
            idempotency_key=f"stage3-q-{doc.id}",
            metadata={"force_ocr_enabled": True, "noop_mode": "ok"},
        )
        DocumentProcessingRepository(db).claim_jobs(worker_id="stage3", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job_q.id, worker_id="stage3"))
        db.refresh(job_q)
        assert job_q.status == "blocked", job_q.status
        print("OK quarantine blocked")

        providers = ocr_svc.list_providers_public()
        assert providers
        print(f"OK providers public count={len(providers)}")
        print("PASS stage3 OCR probes")
        return 0
    finally:
        db.close()
        if not keep:
            tmp_ctx.cleanup()
        else:
            print(f"KEEP probes at {tmp}")


if __name__ == "__main__":
    raise SystemExit(main())
