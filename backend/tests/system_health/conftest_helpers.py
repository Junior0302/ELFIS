"""Helpers SQLite pour tests System Health (sans PostgreSQL réel)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events.event_models import ElfisEvent  # noqa: F401
from app.jobs.job_models import ElfisJob  # noqa: F401
from app.jobs.job_types import JobStatus
from app.search.search_models import ElfisSearchDocument  # noqa: F401


def make_sqlite_session_factory():
    """SQLite mémoire partagé (StaticPool) — compatible ThreadPoolExecutor/timeouts."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def make_job(
    *,
    status: str = JobStatus.PENDING,
    created_at: datetime | None = None,
    completed_at: datetime | None = None,
    locked_at: datetime | None = None,
    heartbeat_at: datetime | None = None,
) -> ElfisJob:
    now = created_at or datetime.utcnow()
    return ElfisJob(
        id=str(uuid4()),
        job_id=str(uuid4()),
        job_name="system.health_check.v1",
        status=status,
        available_at=now,
        created_at=now,
        updated_at=now,
        completed_at=completed_at,
        locked_at=locked_at,
        heartbeat_at=heartbeat_at,
        payload={},
    )


def make_event(
    *,
    status: str = "pending",
    created_at: datetime | None = None,
    locked_at: datetime | None = None,
) -> ElfisEvent:
    now = created_at or datetime.utcnow()
    return ElfisEvent(
        id=str(uuid4()),
        event_id=str(uuid4()),
        event_name="test.event.v1",
        organization_id=1,
        payload={},
        metadata_json={},
        status=status,
        available_at=now,
        created_at=now,
        updated_at=now,
        locked_at=locked_at,
    )
