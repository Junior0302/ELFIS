"""Tests JobService — enqueue, idempotence, cancel, retry."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app import models_saas  # noqa: F401 — FK organizations/users
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.jobs.job_exceptions import JobUnknownTypeError, JobValidationError
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandlerRegistry
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.jobs.handlers.health_handlers import HealthCheckJobHandler


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _svc(db):
    reg = JobHandlerRegistry()
    reg.register(job_name=JobNames.SYSTEM_HEALTH_CHECK, handler=HealthCheckJobHandler())
    return JobService(db, registry=reg)


def test_enqueue_success_and_persisted():
    db = _session()
    result = _svc(db).enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, payload={"message": "hi"})
    )
    assert result.created is True
    assert result.status == JobStatus.PENDING
    job = db.query(ElfisJob).filter(ElfisJob.job_id == result.job_id).one()
    assert job.payload["message"] == "hi"
    assert job.queue_name == "default"


def test_enqueue_scheduled():
    db = _session()
    future = datetime.utcnow() + timedelta(hours=1)
    result = _svc(db).enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, scheduled_at=future)
    )
    assert result.status == JobStatus.SCHEDULED
    assert result.scheduled_at is not None
    job = db.query(ElfisJob).filter(ElfisJob.job_id == result.job_id).one()
    assert job.status == JobStatus.SCHEDULED
    assert job.available_at == future


def test_idempotency_key_prevents_duplicate():
    db = _session()
    svc = _svc(db)
    r1 = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            idempotency_key="health:1",
            payload={"message": "a"},
        )
    )
    r2 = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            idempotency_key="health:1",
            payload={"message": "b"},
        )
    )
    assert r1.job_id == r2.job_id
    assert r2.created is False
    assert r2.idempotent_reuse is True
    assert db.query(ElfisJob).count() == 1


def test_unknown_job_rejected():
    db = _session()
    with pytest.raises(JobUnknownTypeError):
        _svc(db).enqueue(JobRequest(job_name="unknown.job.v1"))


def test_payload_too_large_rejected(monkeypatch):
    import app.jobs.job_service as job_service_mod

    monkeypatch.setattr(job_service_mod.settings, "elfis_job_max_payload_bytes", 256)
    db = _session()
    with pytest.raises(JobValidationError):
        _svc(db).enqueue(
            JobRequest(
                job_name=JobNames.SYSTEM_HEALTH_CHECK,
                payload={"message": "x" * 400},
            )
        )


def test_forbidden_pdf_in_payload():
    db = _session()
    with pytest.raises(JobValidationError):
        _svc(db).enqueue(
            JobRequest(
                job_name=JobNames.SYSTEM_HEALTH_CHECK,
                payload={"pdf_base64": "JVBERi0x"},
            )
        )


def test_cancel_pending():
    db = _session()
    svc = _svc(db)
    r = svc.enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK))
    job = svc.cancel_job(r.job_id)
    assert job.status == JobStatus.CANCELLED
    assert job.cancelled_at is not None


def test_cancel_processing_refused():
    db = _session()
    svc = _svc(db)
    r = svc.enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK))
    job = svc.get_job(r.job_id)
    job.status = JobStatus.PROCESSING
    db.commit()
    with pytest.raises(JobValidationError):
        svc.cancel_job(r.job_id)


def test_manual_retry_platform():
    db = _session()
    svc = _svc(db)
    r = svc.enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK))
    job = svc.get_job(r.job_id)
    job.status = JobStatus.DEAD_LETTER
    job.attempt_count = 5
    job.last_error = "boom"
    db.commit()
    job = svc.retry_job(r.job_id)
    assert job.status == JobStatus.PENDING
    assert job.attempt_count == 0
    assert job.last_error is None


def test_job_created_event_published():
    db = _session()
    _svc(db).enqueue(JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, organization_id=1))
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.event_name == EventNames.JOB_CREATED)
        .all()
    )
    assert len(events) == 1
    assert "payload" not in (events[0].payload or {}) or "message" not in (
        events[0].payload or {}
    )
    assert events[0].payload.get("job_id")
    assert events[0].payload.get("job_name") == JobNames.SYSTEM_HEALTH_CHECK


def test_user_view_hides_payload():
    db = _session()
    svc = _svc(db)
    r = svc.enqueue(
        JobRequest(job_name=JobNames.SYSTEM_HEALTH_CHECK, payload={"message": "secret"})
    )
    view = svc.to_user_view(svc.get_job(r.job_id))
    dumped = view.model_dump()
    assert "payload" not in dumped
    assert "result" not in dumped
    assert "last_error" not in dumped
    assert "locked_by" not in dumped


def test_sanitize_api_key_in_logs():
    from app.jobs.job_logging import sanitize_job_error, safe_job_log_context

    msg = sanitize_job_error("failed api_key=sk-secret-123 password=hunter2")
    assert "sk-secret" not in (msg or "")
    assert "***" in (msg or "")
    ctx = safe_job_log_context(job_id="j1", payload={"x": 1}, api_key="secret")
    assert "payload" not in ctx
    assert "api_key" not in ctx
