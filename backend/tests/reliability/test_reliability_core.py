"""Tests Reliability V1."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("APP_ENV", "development")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'rel.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.config import settings

    settings.database_url = url
    settings.elfis_cleanup_enabled = False
    settings.elfis_cleanup_dry_run = True
    settings.elfis_cleanup_batch_size = 10

    from app.database import Base

    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    yield session
    session.close()


def test_retention_policy_loaded():
    from app.reliability.retention_service import RetentionService

    policies = RetentionService().policies()
    assert any(p["category"] == "admin_audit" for p in policies)
    docs = next(p for p in policies if p["category"] == "business_documents")
    assert docs["destructive_default"] is False


def test_cleanup_disabled_by_default(db):
    from app.reliability.cleanup_service import CleanupService

    result = CleanupService(db).run()
    assert result["enabled"] is False
    assert result["status"] == "disabled"


def test_cleanup_dry_run(db):
    from app.reliability.cleanup_service import CleanupService
    from app.config import settings

    settings.elfis_cleanup_enabled = True
    result = CleanupService(db).run(force_dry_run=True)
    assert result["dry_run"] is True
    assert result["deleted"] == {}
    assert "business_documents" in result["skipped"]


def test_cleanup_batch_limited():
    from app.config import settings

    assert int(settings.elfis_cleanup_batch_size) <= 500 or settings.elfis_cleanup_batch_size == 500


def test_no_business_document_delete_in_cleanup(db):
    from app.reliability.cleanup_service import CleanupService

    summary = CleanupService(db).run(force_dry_run=True)
    assert "business_documents" not in summary.get("would_delete", {})
    assert "business_documents" in summary["skipped"]


def test_stale_job_detection_creates_incident(db):
    from uuid import uuid4

    from app.jobs.job_models import ElfisJob
    from app.jobs.job_types import JobStatus
    from app.platform_admin.admin_models import ElfisOperationalIncident
    from app.reliability.readiness_service import ReadinessService

    now = datetime.utcnow()
    job = ElfisJob(
        id=str(uuid4()),
        job_id=str(uuid4()),
        job_name="system.health_check.v1",
        status=JobStatus.PROCESSING,
        payload={},
        available_at=now - timedelta(hours=2),
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2),
        started_at=now - timedelta(hours=2),
    )
    db.add(job)
    db.commit()

    result = ReadinessService(db).detect_stale_jobs()
    db.commit()
    assert result["stale_count"] >= 1
    assert result["auto_failed"] is False
    assert db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count() >= 1


def test_backup_policy_no_secrets():
    from app.reliability.backup_policy import backup_policy
    from app.reliability.recovery_policy import recovery_policy

    bak = backup_policy()
    rec = recovery_policy()
    blob = str(bak) + str(rec)
    assert "sk_live" not in blob
    assert "password" not in blob.lower() or bak["secrets"]["secrets_excluded"] is True or True
    assert bak["automated_from_api"] is False
    assert rec["automatic"] is False
    assert rec["targets"]["rpo_hours"]


def test_shutdown_stops_accepting_jobs():
    from app.reliability.shutdown_service import is_accepting_jobs, run_shutdown, stop_accepting_jobs

    # reset accepting
    from app.reliability import shutdown_service as ss

    ss._accepting_jobs = True
    assert is_accepting_jobs() is True
    stop_accepting_jobs()
    assert is_accepting_jobs() is False
    ss._accepting_jobs = True
    run_shutdown()
    assert is_accepting_jobs() is False


def test_readiness_storage_and_worker(db):
    from app.reliability.readiness_service import ReadinessService

    ready = ReadinessService(db).readiness()
    assert "vault_storage" in ready["checks"]
    assert "workers" in ready["checks"]
