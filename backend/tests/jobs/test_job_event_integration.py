"""Intégration Event Bus → Job metadata check."""

from __future__ import annotations

import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.events import event_models  # noqa: F401
from app.events.event_bus import DatabaseEventBus
from app.events.event_context import EventContext
from app.events.event_registry import EventHandlerRegistry
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.event_worker import EventWorker
from app.jobs import job_models  # noqa: F401
from app.jobs.handlers.event_bridge import DocumentArchivedMetadataJobHandler
from app.jobs.handlers.health_handlers import HealthCheckJobHandler
from app.jobs.handlers.vault_handlers import VaultDocumentMetadataCheckHandler
from app.jobs.job_models import ElfisJob
from app.jobs.job_registry import JobHandlerRegistry
from app.jobs.job_types import JobNames
from app.jobs import bootstrap_job_handlers


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_document_archived_creates_metadata_job(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_vault_metadata_job_enabled", True)
    db = _session()
    bootstrap_job_handlers()

    event_reg = EventHandlerRegistry()
    event_reg.register(EventNames.VAULT_DOCUMENT_ARCHIVED, DocumentArchivedMetadataJobHandler())
    bus = DatabaseEventBus(db, registry=event_reg)
    bus.publish(
        DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
            organization_id=7,
            aggregate_type="vault_document",
            aggregate_id="vd-1",
            payload={
                "vault_document_id": "vd-1",
                "document_type": "customer_invoice",
                "archive_status": "archived",
            },
            metadata={"source": "test", "actor_user_id": "3"},
            idempotency_key="arch-1",
        )
    )
    EventWorker(db, registry=event_reg, worker_id="ew1").process_next_batch()

    jobs = db.query(ElfisJob).all()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.job_name == JobNames.VAULT_DOCUMENT_METADATA_CHECK
    assert job.idempotency_key == "vault-metadata-check:7:vd-1"
    assert job.payload["vault_document_id"] == "vd-1"
    assert "pdf" not in job.payload


def test_event_bridge_idempotent(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_vault_metadata_job_enabled", True)
    db = _session()
    bootstrap_job_handlers()
    handler = DocumentArchivedMetadataJobHandler()
    event = DomainEvent(
        event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
        organization_id=1,
        payload={"vault_document_id": "d1", "document_type": "customer_invoice"},
        metadata={},
    )
    ctx = EventContext(db=db, worker_id="w", attempt_count=1)
    handler.handle(event, ctx)
    handler.handle(event, ctx)
    assert db.query(ElfisJob).count() == 1


def test_bridge_disabled(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_vault_metadata_job_enabled", False)
    db = _session()
    bootstrap_job_handlers()
    DocumentArchivedMetadataJobHandler().handle(
        DomainEvent(
            event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
            organization_id=1,
            payload={"vault_document_id": "d1"},
        ),
        EventContext(db=db, worker_id="w"),
    )
    assert db.query(ElfisJob).count() == 0
