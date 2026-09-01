"""Enqueue des jobs de synchronisation bancaire — Job Queue existante uniquement."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection
from app.banking.sync_status import mark_sync_queued
from app.config import settings
from app.jobs.job_schemas import JobRequest, JobResult
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames
from app.observability.metrics import metrics_registry

logger = logging.getLogger(__name__)

SYNC_TRIGGERS = frozenset({"manual", "consent", "webhook", "scheduled", "recovery"})


class BankingSyncEnqueueError(Exception):
    pass


def _safe_log(
    event: str,
    *,
    organization_id: int | None = None,
    connection_id: int | None = None,
    provider: str | None = None,
    trigger: str | None = None,
    **extra: Any,
) -> None:
    payload = {
        "organization_id": organization_id,
        "connection_id": connection_id,
        "provider": provider,
        "trigger": trigger,
    }
    payload.update(extra)
    logger.info(event, extra={k: v for k, v in payload.items() if v is not None})


def enqueue_connection_sync(
    db: Session,
    *,
    organization_id: int,
    connection_id: int,
    trigger: str,
    correlation_id: str | None = None,
    scheduled_at: datetime | None = None,
    idempotency_key: str | None = None,
    provider: str | None = None,
) -> JobResult:
    trigger = (trigger or "").strip()
    if trigger not in SYNC_TRIGGERS:
        raise BankingSyncEnqueueError(f"Trigger de synchronisation inconnu: {trigger}")

    connection = (
        db.query(ElfisBankConnection)
        .filter(
            ElfisBankConnection.id == connection_id,
            ElfisBankConnection.organization_id == organization_id,
        )
        .one_or_none()
    )
    if connection is None:
        raise BankingSyncEnqueueError("Connexion bancaire introuvable.")

    from app.banking.consent import needs_reauth

    if needs_reauth(connection) and trigger != "consent":
        raise BankingSyncEnqueueError("Une action utilisateur est requise avant de synchroniser.")

    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()
    corr = (correlation_id or "").strip() or str(uuid4())
    result = JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.BANKING_SYNC_CONNECTION,
            organization_id=organization_id,
            payload={
                "organization_id": organization_id,
                "connection_id": connection_id,
                "trigger": trigger,
                "correlation_id": corr,
            },
            idempotency_key=idempotency_key,
            correlation_id=corr,
            scheduled_at=scheduled_at,
            max_attempts=max(1, int(settings.banking_sync_job_max_attempts)),
        )
    )
    if result.created:
        mark_sync_queued(connection)
        db.add(connection)
        db.commit()
        metrics_registry.incr(
            "elfis_banking_sync_queued_total",
            labels={"trigger": trigger, "provider": connection.provider},
        )
        _safe_log(
            "banking_sync_queued",
            organization_id=organization_id,
            connection_id=connection_id,
            provider=provider or connection.provider,
            trigger=trigger,
            job_id=result.job_id,
            correlation_id=corr,
        )
    return result


def should_run_inline(trigger: str) -> bool:
    """Sans worker Render, conserver le sync manuel/consentement in-request."""
    if settings.elfis_job_worker_enabled:
        return False
    return trigger in {"manual", "consent"}


def request_connection_sync(
    db: Session,
    *,
    organization_id: int,
    connection_id: int,
    trigger: str,
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
):
    """Enqueue (workers on) or exécute le SyncEngine (workers off, manual/consent)."""
    from app.banking.sync_engine import SyncEngine

    if should_run_inline(trigger):
        return {
            "queued": False,
            "job": None,
            "runs": SyncEngine(db).run_sync(
                organization_id,
                connection_id=connection_id,
                trigger=trigger,
            ),
        }
    job = enqueue_connection_sync(
        db,
        organization_id=organization_id,
        connection_id=connection_id,
        trigger=trigger,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )
    return {"queued": True, "job": job, "runs": []}


def request_organization_sync(
    db: Session,
    *,
    organization_id: int,
    connection_id: int | None = None,
    trigger: str = "manual",
    correlation_id: str | None = None,
):
    from app.banking.engine import BankingEngine
    from app.banking.sync_engine import SyncEngine
    from app.banking.banking_types import ConnectionStatus

    if should_run_inline(trigger):
        return {
            "queued": False,
            "jobs": [],
            "runs": SyncEngine(db).run_sync(
                organization_id,
                connection_id=connection_id,
                trigger=trigger,
            ),
        }
    engine = BankingEngine(db)
    if connection_id is not None:
        connections = [engine.get_connection(organization_id, connection_id)]
    else:
        connections = [
            c
            for c in engine.list_connections(organization_id)
            if c.status
            in {ConnectionStatus.connected.value, ConnectionStatus.error.value}
            and (c.provider_connection_id or "").strip()
        ]
        from app.banking.consent import needs_reauth

        connections = [c for c in connections if not needs_reauth(c)]
    if not connections:
        from app.banking.engine import BankingEngineError

        raise BankingEngineError(
            "Aucune connexion bancaire active. Connectez d'abord une banque."
        )
    jobs = [
        enqueue_connection_sync(
            db,
            organization_id=organization_id,
            connection_id=c.id,
            trigger=trigger,
            correlation_id=correlation_id,
            provider=c.provider,
        )
        for c in connections
    ]
    return {"queued": True, "jobs": jobs, "runs": []}


def hour_bucket(now: datetime | None = None) -> str:
    stamp = now or datetime.utcnow()
    return stamp.strftime("%Y%m%d%H")


def connection_sync_idempotency_key(
    connection_id: int, trigger: str, *, now: datetime | None = None
) -> str:
    return f"banking-sync-{int(connection_id)}-{trigger}-{hour_bucket(now)}"


def sweep_idempotency_key(*, now: datetime | None = None) -> str:
    return f"banking-sync-sweep-{hour_bucket(now)}"


def enqueue_sync_sweep(
    db: Session,
    *,
    scheduled_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> JobResult:
    from app.jobs import bootstrap_job_handlers

    bootstrap_job_handlers()
    return JobService(db).enqueue(
        JobRequest(
            job_name=JobNames.BANKING_SYNC_SWEEP,
            payload=dict(payload or {}),
            scheduled_at=scheduled_at,
            idempotency_key=sweep_idempotency_key(now=now),
            max_attempts=3,
        )
    )


def delayed_schedule(jitter_seconds: int) -> datetime:
    from random import randint

    delay = randint(0, max(0, jitter_seconds))
    return datetime.utcnow() + timedelta(seconds=delay)
