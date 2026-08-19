"""WORKER — démarrage / config."""

from __future__ import annotations

from app.jobs.job_worker import default_job_worker_id, parse_queues
from app.reliability.shutdown_service import is_accepting_jobs, run_shutdown, stop_accepting_jobs


def test_worker_001_worker_ids_and_queues():
    wid = default_job_worker_id()
    assert isinstance(wid, str) and len(wid) > 0
    queues = parse_queues()
    assert isinstance(queues, (list, tuple))


def test_worker_002_bootstrap_handlers_no_network():
    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()


def test_worker_003_graceful_shutdown_stops_accepting():
    # Réinitialiser état module
    from app.reliability import shutdown_service as ss

    ss._accepting_jobs = True  # noqa: SLF001
    assert is_accepting_jobs() is True
    stop_accepting_jobs()
    assert is_accepting_jobs() is False
    ss._accepting_jobs = True  # noqa: SLF001
    run_shutdown()
    assert is_accepting_jobs() is False
