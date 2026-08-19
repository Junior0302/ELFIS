"""RC1 — pool SQLAlchemy + preuve SKIP LOCKED dans le code."""

from __future__ import annotations

import inspect

from app.events.event_repository import EventRepository
from app.jobs.job_repository import JobRepository
from tests.concurrency.postgres_helpers import (
    checked_out_connections,
    make_pg_session_factory,
    pg_version,
    require_postgres,
)


def test_skip_locked_present_in_repositories():
    assert "FOR UPDATE SKIP LOCKED" in inspect.getsource(JobRepository._claim_jobs_postgres)
    assert "FOR UPDATE SKIP LOCKED" in inspect.getsource(EventRepository._claim_events_postgres)


def test_normalize_postgres_url_uses_psycopg():
    from scripts.rc1.safety import normalize_postgres_url

    assert normalize_postgres_url("postgresql://u:p@h/db").startswith("postgresql+psycopg://")


def test_postgres_pool_no_leak_after_sessions():
    require_postgres()
    Session, engine = make_pg_session_factory()
    before = checked_out_connections(engine)
    sessions = [Session() for _ in range(8)]
    for s in sessions:
        s.execute(__import__("sqlalchemy").text("SELECT 1"))
    mid = checked_out_connections(engine)
    for s in sessions:
        s.close()
    after = checked_out_connections(engine)
    assert after <= before + 1, f"fuite pool before={before} mid={mid} after={after}"
    assert pg_version(engine)
    engine.dispose()
