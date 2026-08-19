"""Tests policies, pipeline registry, health, worker once."""

from __future__ import annotations

import asyncio
import os

import pytest

from app.document_processing.policies import ProcessingRetryPolicy
from app.document_processing.step_registry import get_pipeline_registry
from app.document_processing.types import PIPELINE_BASIC_V1
from app.document_processing.worker import process_once
from app.system_health.providers.document_processing_health_provider import (
    DocumentProcessingHealthProvider,
)
from app.system_health.health_types import HealthStatus
from tests.document_processing.conftest_helpers import make_processing_db, seed_document, seed_org_user
from app.document_processing.service import DocumentProcessingService


def test_retry_policy_backoff():
    p = ProcessingRetryPolicy(
        max_attempts=5,
        initial_delay_seconds=10,
        max_delay_seconds=100,
        backoff_multiplier=2.0,
        jitter=False,
    )
    assert p.delay_seconds(1) == 10
    assert p.delay_seconds(2) == 20
    assert p.delay_seconds(5) == 100
    assert p.is_retryable("noop_retryable")
    assert not p.is_retryable("document_purged")
    assert not p.is_retryable("permission_denied")


def test_pipeline_registry_known():
    reg = get_pipeline_registry()
    pipe = reg.get_pipeline(PIPELINE_BASIC_V1)
    assert [s.key for s in pipe.steps] == [
        "validate_document_available",
        "inspect_storage_metadata",
        "noop_processing",
        "finalize_processing",
    ]
    assert reg.get_handler("noop_processing")


def test_health_provider_empty_queue(monkeypatch):
    factory, engine = make_processing_db()
    db = factory()

    class _S:
        def __call__(self):
            return factory()

    monkeypatch.setattr(
        "app.system_health.providers.document_processing_health_provider.SessionLocal",
        _S(),
    )
    result = DocumentProcessingHealthProvider().check_health()
    assert result.status == HealthStatus.HEALTHY
    assert result.service_id == "document_processing"
    db.close()
    engine.dispose()


def test_worker_process_once(tmp_path, monkeypatch):
    factory, engine = make_processing_db()
    db = factory()
    org, user = seed_org_user(db)
    doc = seed_document(db, tmp_path, org, user)
    DocumentProcessingService(db).create_job(organization_id=org.id, document_id=doc.id)
    db.close()

    monkeypatch.setattr(
        "app.document_processing.worker.SessionLocal",
        lambda: factory(),
    )
    n = asyncio.run(process_once(worker_id="cli-once", max_jobs=1))
    assert n == 1
    db2 = factory()
    from app.document_processing.models import ElfisDocumentProcessingJob

    job = db2.query(ElfisDocumentProcessingJob).one()
    assert job.status == "completed"
    db2.close()
    engine.dispose()


def test_worker_cli_requires_env(monkeypatch):
    monkeypatch.delenv("ELFIS_ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    from scripts.processing.worker import main

    assert main(["--once"]) == 2
