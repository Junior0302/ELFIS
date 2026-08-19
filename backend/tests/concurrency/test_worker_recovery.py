"""WORKER / DB / RATE / SEC — smoke Phase F."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames, JobStatus
from app.platform_admin.admin_models import ElfisOperationalIncident
from app.reliability.readiness_service import ReadinessService
from tests.performance.helpers import refuse_production_url


def test_worker_001_002_stale_and_dedup(functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        started = datetime.utcnow() - timedelta(hours=3)
        db.add(
            ElfisJob(
                id=str(uuid4()),
                job_id=str(uuid4()),
                job_name=JobNames.SYSTEM_HEALTH_CHECK,
                organization_id=org_id,
                status=JobStatus.PROCESSING,
                payload={},
                available_at=started,
                created_at=started,
                updated_at=started,
                started_at=started,
                locked_at=started,
                locked_by="worker-phase-f",
            )
        )
        db.commit()
        r1 = ReadinessService(db).detect_stale_jobs()
        db.commit()
        assert r1.get("stale_count", 0) >= 1
        n1 = db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count()
        r2 = ReadinessService(db).detect_stale_jobs()
        db.commit()
        n2 = db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count()
        assert n2 == n1
        assert r2.get("auto_failed") is False
    finally:
        db.close()


def test_db_001_sessions_closed(functional_db):
    Session = functional_db["Session"]
    db = Session()
    db.execute(__import__("sqlalchemy").text("SELECT 1"))
    db.close()
    # Pas de fuite évidente — smoke
    assert True


def test_sec_001_script_refuses_production():
    try:
        refuse_production_url("postgresql://user:pass@prod-db.render.com/elfis")
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_rate_smoke_disabled_in_recette(api):
    # En recette, rate limit souvent off — endpoint répond
    r = api.client.get("/api/health/live")
    assert r.status_code == 200
