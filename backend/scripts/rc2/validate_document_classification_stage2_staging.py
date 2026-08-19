"""Probe staging RC2.5.2 — classification déterministe (pas d'OCR/IA)."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip()
    if not env:
        raise SystemExit("FATAL: ELFIS_ENVIRONMENT requis")
    print(f"ELFIS_ENVIRONMENT={env}")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.audit import audit_models  # noqa: F401
    from app.database import Base
    from app.document_processing import models as dp_models  # noqa: F401
    from app.document_processing.classification import models as cls_models  # noqa: F401
    from app.document_processing.classification.service import DocumentClassificationService
    from app.document_processing.orchestrator import DocumentProcessingOrchestrator
    from app.document_processing.repository import DocumentProcessingRepository
    from app.document_processing.service import DocumentProcessingService
    from app.document_processing.step_registry import reset_pipeline_registry_for_tests
    from app.document_processing.types import PIPELINE_CLASSIFICATION_V1
    from app.models_saas import Organization, User
    from app.storage import storage_models  # noqa: F401
    from app.storage.document_registry_service import DocumentRegistryService
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_context import StorageContext

    reset_pipeline_registry_for_tests()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    org = Organization(name="CLS Probe")
    db.add(org)
    db.flush()
    user = User(
        first_name="P",
        last_name="C",
        email=f"cls-{uuid4().hex[:8]}@example.invalid",
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "obj"
        root.mkdir()
        reg = DocumentRegistryService(
            db,
            context=StorageContext(provider=LocalStorageProvider(root=root), namespace="probe"),
        )

        def make(name: str) -> object:
            return reg.create_from_upload(
                organization_id=org.id,
                filename=name,
                content=b"%PDF-1.4 probe\n%%EOF",
                declared_mime="application/pdf",
                owner_user_id=user.id,
                title=name,
            )

        facture = make("facture-probe.pdf")
        devis = make("devis-probe.pdf")
        ambigu = make("document.pdf")
        print("OK probes created")

        svc_job = DocumentProcessingService(db)
        cls_svc = DocumentClassificationService(db)

        for doc, label in ((facture, "facture"), (devis, "devis"), (ambigu, "ambigu")):
            job = svc_job.create_job(
                organization_id=org.id,
                document_id=doc.id,
                pipeline_key=PIPELINE_CLASSIFICATION_V1,
                idempotency_key=f"stage2-{label}-{doc.id}",
            )
            DocumentProcessingRepository(db).claim_jobs(worker_id="stage2", batch_size=1, lease_seconds=60)
            asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="stage2"))
            db.refresh(job)
            assert job.status == "completed", job.status
            items, _ = cls_svc.list_classifications(organization_id=org.id, document_id=doc.id)
            assert items, label
            row = items[0]
            print(
                f"OK {label}: predicted={row.predicted_type} score={row.confidence_score} review={row.requires_review}"
            )
            assert row.document_version_id == doc.current_version_id

        # confirm devis
        items, _ = cls_svc.list_classifications(organization_id=org.id, document_id=devis.id)
        confirmed = cls_svc.confirm(items[0].id, org.id, confirmed_type="quote", actor_user_id=user.id)
        assert confirmed.confirmed_type == "quote"
        print("OK confirm")

        # reject facture proposal (or confirm then separate)
        items_f, _ = cls_svc.list_classifications(organization_id=org.id, document_id=facture.id)
        if items_f[0].status == "proposed":
            rejected = cls_svc.reject(items_f[0].id, org.id, reason="probe")
            assert rejected.status == "rejected"
            print("OK reject")

        job_r = cls_svc.request_reclassify(confirmed.id, org.id, force=True)
        assert job_r.pipeline_key == PIPELINE_CLASSIFICATION_V1
        print("OK reclassify job")

        org2 = Organization(name="Other")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        try:
            cls_svc.get_for_org(confirmed.id, org2.id)
            raise AssertionError("cross-tenant")
        except Exception:
            print("OK tenant")

        for model in (
            cls_models.ElfisDocumentClassification,
            dp_models.ElfisDocumentProcessingAttempt,
            dp_models.ElfisDocumentProcessingStep,
            dp_models.ElfisDocumentProcessingJob,
        ):
            db.query(model).delete()
        db.commit()
        print("OK cleanup")

    db.close()
    engine.dispose()
    print("RC2.5.2 staging probe OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
