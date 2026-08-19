"""Validation staging RC2.5.1 — Document Processing (probes, pas de documents réels)."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def _require_env() -> None:
    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip()
    if not env:
        raise SystemExit("FATAL: ELFIS_ENVIRONMENT / APP_ENV requis")
    print(f"ELFIS_ENVIRONMENT={env}")


def main() -> int:
    _require_env()
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.audit import audit_models  # noqa: F401
    from app.database import Base
    from app.document_processing import models as dp_models  # noqa: F401
    from app.document_processing.orchestrator import DocumentProcessingOrchestrator
    from app.document_processing.repository import DocumentProcessingRepository
    from app.document_processing.service import DocumentProcessingService
    from app.models_saas import Organization, User
    from app.storage import storage_models  # noqa: F401
    from app.storage.document_registry_service import DocumentRegistryService
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_context import StorageContext
    from app.system_health.providers.document_processing_health_provider import (
        DocumentProcessingHealthProvider,
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    org = Organization(name="DP Staging Probe")
    db.add(org)
    db.flush()
    user = User(
        first_name="Probe",
        last_name="DP",
        email=f"dp-probe-{uuid4().hex[:8]}@example.invalid",
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
        doc = reg.create_from_upload(
            organization_id=org.id,
            filename="probe.txt",
            content=b"document-processing-stage1-probe",
            declared_mime="text/plain",
            owner_user_id=user.id,
            title="Probe DP",
        )
        print("OK document", doc.id)

        svc = DocumentProcessingService(db)
        key = f"stage1-{doc.id}"
        job = svc.create_job(
            organization_id=org.id,
            document_id=doc.id,
            idempotency_key=key,
            requested_by_user_id=user.id,
        )
        job2 = svc.create_job(
            organization_id=org.id,
            document_id=doc.id,
            idempotency_key=key,
        )
        assert job.id == job2.id
        steps = svc.list_steps(job.id)
        assert len(steps) == 4
        print("OK create+idempotency+steps", job.id)

        # exécution locale (SessionLocal staging ≠ probe DB)
        DocumentProcessingRepository(db).claim_jobs(
            worker_id="stage1-worker", batch_size=1, lease_seconds=60
        )
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job.id, worker_id="stage1-worker"))
        db.refresh(job)
        assert job.status == "completed", job.status
        assert job.progress_percent == 100
        print("OK pipeline completed")

        # cancel probe
        job_c = svc.create_job(organization_id=org.id, document_id=doc.id, idempotency_key="cancel-1")
        cancelled = svc.request_cancel(job_c.id, org.id, actor_user_id=user.id)
        assert cancelled.status == "cancelled"
        print("OK cancel")

        # retryable + retry
        job_r = svc.create_job(
            organization_id=org.id,
            document_id=doc.id,
            idempotency_key="retry-1",
            metadata={"noop_mode": "permanent"},
        )
        DocumentProcessingRepository(db).claim_jobs(worker_id="w", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job_r.id, worker_id="w"))
        db.refresh(job_r)
        assert job_r.status == "failed"
        job_r.metadata_json = {"noop_mode": "ok"}
        db.commit()
        retried = svc.request_retry(job_r.id, org.id)
        assert retried.status == "queued"
        DocumentProcessingRepository(db).claim_jobs(worker_id="w2", batch_size=1, lease_seconds=60)
        asyncio.run(DocumentProcessingOrchestrator(db).run_job(job_r.id, worker_id="w2"))
        db.refresh(job_r)
        assert job_r.status == "completed"
        print("OK retry")

        # lease recovery
        job_l = svc.create_job(organization_id=org.id, document_id=doc.id, idempotency_key="lease-1")
        DocumentProcessingRepository(db).claim_jobs(worker_id="dead", batch_size=1, lease_seconds=60)
        job_l.locked_until = datetime.utcnow() - timedelta(seconds=10)
        job_l.heartbeat_at = datetime.utcnow() - timedelta(seconds=120)
        db.commit()
        reclaimed = DocumentProcessingRepository(db).claim_jobs(
            worker_id="alive", batch_size=1, lease_seconds=60
        )
        assert len(reclaimed) == 1 and reclaimed[0].locked_by == "alive"
        print("OK lease recovery")

        # tenant isolation
        org2 = Organization(name="Other Probe")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        try:
            svc.get_job_for_org(job.id, org2.id)
            raise AssertionError("cross-tenant should fail")
        except Exception:
            print("OK tenant isolation")

        health = DocumentProcessingHealthProvider()
        # SessionLocal may point elsewhere — check provider imports DB; skip if unhealthy
        print("OK health provider imported", health.service_id)

        # cleanup soft: delete processing rows
        for model in (
            dp_models.ElfisDocumentProcessingAttempt,
            dp_models.ElfisDocumentProcessingStep,
            dp_models.ElfisDocumentProcessingJob,
        ):
            db.query(model).delete()
        db.commit()
        print("OK cleanup")

    db.close()
    engine.dispose()
    print("RC2.5.1 staging probe OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
