"""BANK-4 — jobs, retries, état de sync, isolation."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import pytest

from app.banking.banking_models import ElfisBankConnection
from app.banking.connectors import registry
from app.banking.engine import BankingEngine, SyncAlreadyInProgressError
from app.banking.sync_engine import SyncEngine
from app.banking.sync_jobs import enqueue_connection_sync, request_connection_sync
from app.banking.sweep import select_stale_connections
from app.config import settings
from app.jobs import bootstrap_job_handlers
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobStatus
from app.jobs.job_worker import JobWorker
from app.models import BankTransaction
from app.observability.metrics import metrics_registry

from tests.banking.conftest_helpers import (
    FakeBankConnector,
    make_banking_session_factory,
    make_tx,
    seed_org,
)


@pytest.fixture()
def bank4_ctx(monkeypatch):
    monkeypatch.setattr(settings, "elfis_job_worker_enabled", True)
    metrics_registry.reset()
    bootstrap_job_handlers()
    factory, engine = make_banking_session_factory()
    db = factory()
    org = seed_org(db)
    connector = FakeBankConnector(
        transactions={
            "fake-acc-1": [
                make_tx("fake-acc-1", date(2026, 7, 1), "VIREMENT CLIENT ALPHA", 500.0),
            ]
        }
    )
    registry.register_connector("fake", lambda: connector)
    connection = BankingEngine(db).connect(
        organization_id=org.id, provider="fake", bank_name="Banque Factice"
    )
    yield {
        "db": db,
        "factory": factory,
        "engine": engine,
        "org": org,
        "connection": connection,
        "connector": connector,
    }
    registry.unregister_connector("fake")
    db.close()


def _process(ctx) -> int:
    return JobWorker(
        ctx["db"],
        worker_id="w-bank4",
        session_factory=ctx["factory"],
    ).process_next_batch()


def test_manual_trigger_enqueues_job(bank4_ctx, monkeypatch):
    ctx = bank4_ctx
    result = enqueue_connection_sync(
        ctx["db"],
        organization_id=ctx["org"].id,
        connection_id=ctx["connection"].id,
        trigger="manual",
    )
    assert result.created is True
    job = ctx["db"].query(ElfisJob).filter(ElfisJob.job_id == result.job_id).one()
    assert job.job_name == "banking.sync_connection.v1"
    assert job.payload["trigger"] == "manual"
    assert job.payload["organization_id"] == ctx["org"].id
    assert job.payload["connection_id"] == ctx["connection"].id
    ctx["db"].refresh(ctx["connection"])
    assert ctx["connection"].last_sync_status == "queued"


def test_consent_trigger_enqueues_job(bank4_ctx):
    result = enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="consent",
        idempotency_key="banking-sync-consent-test",
    )
    assert result.created is True
    job = bank4_ctx["db"].query(ElfisJob).filter(ElfisJob.job_id == result.job_id).one()
    assert job.payload["trigger"] == "consent"


def test_worker_calls_sync_engine(bank4_ctx):
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="manual",
    )
    assert _process(bank4_ctx) == 1
    assert bank4_ctx["connector"].refresh_calls >= 1
    job = bank4_ctx["db"].query(ElfisJob).one()
    assert job.status == JobStatus.COMPLETED
    bank4_ctx["db"].refresh(bank4_ctx["connection"])
    assert bank4_ctx["connection"].last_sync_status == "success"
    assert bank4_ctx["connection"].consecutive_sync_failures == 0


def test_retry_timeout_and_5xx(bank4_ctx):
    bank4_ctx["connector"].fail_times = 1
    bank4_ctx["connector"].fail_retryable = True
    bank4_ctx["connector"].fail_status_code = 503
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="scheduled",
        idempotency_key="retry-5xx",
    )
    _process(bank4_ctx)
    job = bank4_ctx["db"].query(ElfisJob).filter(ElfisJob.idempotency_key == "retry-5xx").one()
    assert job.status == JobStatus.RETRY
    bank4_ctx["db"].refresh(bank4_ctx["connection"])
    assert bank4_ctx["connection"].last_sync_status == "failed"
    assert bank4_ctx["connection"].consecutive_sync_failures == 1
    assert bank4_ctx["connection"].last_sync_error_code in {
        "provider_unavailable",
        "network",
        "timeout",
    }


def test_no_retry_permanent_4xx(bank4_ctx):
    bank4_ctx["connector"].fail_times = 3
    bank4_ctx["connector"].fail_retryable = False
    bank4_ctx["connector"].fail_status_code = 401
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="scheduled",
        idempotency_key="perm-401",
    )
    _process(bank4_ctx)
    job = bank4_ctx["db"].query(ElfisJob).filter(ElfisJob.idempotency_key == "perm-401").one()
    assert job.status == JobStatus.FAILED
    bank4_ctx["db"].refresh(bank4_ctx["connection"])
    assert bank4_ctx["connection"].last_sync_error_code == "provider_unauthorized"
    assert bank4_ctx["connection"].consecutive_sync_failures == 1


def test_already_in_progress_does_not_retry_storm(bank4_ctx, monkeypatch):
    def _busy(*args, **kwargs):
        raise SyncAlreadyInProgressError("Une synchronisation est déjà en cours.")

    monkeypatch.setattr(SyncEngine, "run_sync", _busy)
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="webhook",
        idempotency_key="in-progress",
    )
    _process(bank4_ctx)
    job = bank4_ctx["db"].query(ElfisJob).filter(ElfisJob.idempotency_key == "in-progress").one()
    assert job.status == JobStatus.COMPLETED
    assert (job.result or {}).get("reason") == "already_in_progress"


def test_success_resets_failure_count(bank4_ctx):
    connection = bank4_ctx["connection"]
    connection.consecutive_sync_failures = 4
    connection.last_sync_status = "failed"
    connection.last_sync_error_code = "timeout"
    bank4_ctx["db"].add(connection)
    bank4_ctx["db"].commit()
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=connection.id,
        trigger="recovery",
    )
    _process(bank4_ctx)
    bank4_ctx["db"].refresh(connection)
    assert connection.last_sync_status == "success"
    assert connection.consecutive_sync_failures == 0
    assert connection.last_sync_error_code is None


def test_failure_increments_count(bank4_ctx):
    bank4_ctx["connector"].fail_times = 2
    bank4_ctx["connector"].fail_retryable = False
    bank4_ctx["connector"].fail_status_code = 400
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="scheduled",
    )
    _process(bank4_ctx)
    bank4_ctx["db"].refresh(bank4_ctx["connection"])
    assert bank4_ctx["connection"].consecutive_sync_failures == 1
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="recovery",
        idempotency_key="fail-2",
    )
    _process(bank4_ctx)
    bank4_ctx["db"].refresh(bank4_ctx["connection"])
    assert bank4_ctx["connection"].consecutive_sync_failures == 2


def test_scheduler_only_stale_eligible(bank4_ctx):
    db = bank4_ctx["db"]
    org = bank4_ctx["org"]
    stale = bank4_ctx["connection"]
    stale.last_sync_at = datetime.utcnow() - timedelta(hours=48)
    stale.next_sync_at = datetime.utcnow() - timedelta(hours=1)
    stale.status = "connected"
    db.add(stale)

    fresh = BankingEngine(db).connect(
        organization_id=org.id, provider="fake", bank_name="Fraiche"
    )
    # connect() is idempotent per provider — force a second row
    fresh.id  # may be same connection
    other_org = seed_org(db, "Org B")
    other = ElfisBankConnection(
        organization_id=other_org.id,
        provider="fake",
        provider_connection_id="other-item",
        bank_name="Autre",
        status="connected",
        last_sync_at=datetime.utcnow() - timedelta(hours=48),
        last_sync_status="success",
    )
    disconnected = ElfisBankConnection(
        organization_id=org.id,
        provider="fake",
        provider_connection_id="disc-item",
        bank_name="Coupée",
        status="disconnected",
        last_sync_at=datetime.utcnow() - timedelta(hours=72),
        last_sync_status="success",
    )
    reauth = ElfisBankConnection(
        organization_id=org.id,
        provider="fake",
        provider_connection_id="reauth-item",
        bank_name="SCA",
        status="error",
        last_sync_error_code="consent_expired",
        last_sync_at=datetime.utcnow() - timedelta(hours=72),
        last_sync_status="failed",
    )
    db.add_all([other, disconnected, reauth])
    db.commit()

    selected = select_stale_connections(db, stale_hours=24, limit=50)
    ids = {c.id for c in selected}
    assert stale.id in ids
    assert other.id in ids
    assert disconnected.id not in ids
    assert reauth.id not in ids
    by_id = {c.id: c for c in selected}
    assert by_id[other.id].organization_id == other_org.id
    assert by_id[stale.id].organization_id == org.id


def test_tenant_isolation_enqueue(bank4_ctx):
    other = seed_org(bank4_ctx["db"], "Org Isolée")
    with pytest.raises(Exception):
        enqueue_connection_sync(
            bank4_ctx["db"],
            organization_id=other.id,
            connection_id=bank4_ctx["connection"].id,
            trigger="manual",
        )


def test_no_secrets_in_logs_or_job_payload(bank4_ctx, caplog):
    caplog.set_level(logging.INFO)
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="manual",
        idempotency_key="log-safe",
    )
    _process(bank4_ctx)
    blob = " ".join(r.getMessage() for r in caplog.records) + str(caplog.text)
    assert "Client-Secret" not in blob
    assert "client_secret" not in blob.lower()
    job = bank4_ctx["db"].query(ElfisJob).filter(ElfisJob.idempotency_key == "log-safe").one()
    payload = str(job.payload)
    assert "secret" not in payload.lower()
    assert "iban" not in payload.lower()
    assert "token" not in payload.lower()


def test_worker_crash_retry_is_idempotent(bank4_ctx):
    bank4_ctx["connector"].fail_times = 1
    bank4_ctx["connector"].fail_retryable = True
    bank4_ctx["connector"].fail_status_code = 503
    enqueue_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="scheduled",
        idempotency_key="crash-retry",
    )
    _process(bank4_ctx)
    job = bank4_ctx["db"].query(ElfisJob).filter(ElfisJob.idempotency_key == "crash-retry").one()
    assert job.status == JobStatus.RETRY
    job.available_at = datetime.utcnow() - timedelta(seconds=1)
    bank4_ctx["db"].add(job)
    bank4_ctx["db"].commit()
    _process(bank4_ctx)
    bank4_ctx["db"].refresh(job)
    assert job.status == JobStatus.COMPLETED
    txs = bank4_ctx["db"].query(BankTransaction).all()
    labels = [t.label for t in txs]
    assert labels.count("VIREMENT CLIENT ALPHA") == 1


def test_inline_manual_when_workers_disabled(bank4_ctx, monkeypatch):
    monkeypatch.setattr(settings, "elfis_job_worker_enabled", False)
    outcome = request_connection_sync(
        bank4_ctx["db"],
        organization_id=bank4_ctx["org"].id,
        connection_id=bank4_ctx["connection"].id,
        trigger="manual",
    )
    assert outcome["queued"] is False
    assert outcome["runs"]
    assert outcome["runs"][0].status == "completed"


def test_sweep_enqueue_is_idempotent_same_hour(bank4_ctx):
    from app.banking.sync_jobs import enqueue_sync_sweep, sweep_idempotency_key
    from datetime import datetime

    frozen = datetime(2026, 8, 27, 15, 10, 0)
    first = enqueue_sync_sweep(bank4_ctx["db"], payload={"source": "a"}, now=frozen)
    second = enqueue_sync_sweep(bank4_ctx["db"], payload={"source": "b"}, now=frozen)
    assert first.created is True
    assert second.created is False
    assert second.idempotent_reuse is True
    assert first.job_id == second.job_id
    assert sweep_idempotency_key(now=frozen) == "banking-sync-sweep-2026082715"
    jobs = bank4_ctx["db"].query(ElfisJob).filter(
        ElfisJob.job_name == "banking.sync_sweep.v1"
    ).all()
    assert len(jobs) == 1


def test_sweep_handler_does_not_storm_connection_jobs(bank4_ctx, monkeypatch):
    from app.jobs.handlers.banking_handlers import BankingSyncSweepJobHandler
    from app.jobs.job_context import JobContext
    from app.jobs.job_models import ElfisJob
    from datetime import datetime, timedelta

    monkeypatch.setattr(settings, "banking_sync_sweep_jitter_seconds", 0)
    connection = bank4_ctx["connection"]
    connection.last_sync_at = datetime.utcnow() - timedelta(hours=48)
    connection.next_sync_at = datetime.utcnow() - timedelta(hours=1)
    connection.status = "connected"
    bank4_ctx["db"].add(connection)
    bank4_ctx["db"].commit()

    handler = BankingSyncSweepJobHandler()
    job = ElfisJob(
        job_id="sweep-1",
        job_name="banking.sync_sweep.v1",
        payload={"limit": 50},
        status="processing",
        organization_id=None,
    )
    ctx = JobContext(
        job_id="sweep-1",
        organization_id=None,
        user_id=None,
        correlation_id=None,
        attempt_number=1,
        worker_id="w",
        db=bank4_ctx["db"],
    )
    first = handler.handle(job, ctx)
    second = handler.handle(job, ctx)
    assert first.result["queued"] >= 1
    assert second.result["queued"] == 0
    assert second.result["skipped"] >= 1
    sync_jobs = [
        j
        for j in bank4_ctx["db"].query(ElfisJob).all()
        if j.job_name == "banking.sync_connection.v1"
        and (j.payload or {}).get("trigger") in {"scheduled", "recovery"}
    ]
    assert len(sync_jobs) == 1
