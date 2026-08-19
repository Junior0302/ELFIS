"""CONC-001 — Jobs claimés une seule fois (SQLite StaticPool)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.jobs import job_models  # noqa: F401
from app.jobs.job_models import ElfisJob
from app.jobs.job_repository import JobRepository
from app.jobs.job_types import JobNames, JobStatus
from app.events import event_models  # noqa: F401


def test_conc_001_jobs_claimed_once():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    now = datetime.utcnow()
    for _ in range(5):
        db.add(
            ElfisJob(
                id=str(uuid4()),
                job_id=str(uuid4()),
                job_name=JobNames.SYSTEM_HEALTH_CHECK,
                status=JobStatus.PENDING,
                payload={},
                queue_name="default",
                available_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()

    s1, s2 = Session(), Session()
    try:
        a = JobRepository(s1).claim_jobs(
            worker_id="w-a", queues=["default"], batch_size=10, lock_timeout_seconds=60
        )
        s1.commit()
        b = JobRepository(s2).claim_jobs(
            worker_id="w-b", queues=["default"], batch_size=10, lock_timeout_seconds=60
        )
        s2.commit()
        ids_a = {j.job_id for j in a}
        ids_b = {j.job_id for j in b}
        assert ids_a.isdisjoint(ids_b)
        assert len(ids_a) + len(ids_b) == 5
    finally:
        s1.close()
        s2.close()
        db.close()
