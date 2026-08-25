"""Publication des événements Banking — consommés par le Dashboard et l'Assistant IA.

Convention plateforme ``module.entity.action.vN`` :
- transaction_created  -> banking.transaction.created.v1
- transaction_updated  -> banking.transaction.updated.v1
- sync_completed       -> banking.sync.completed.v1

Les payloads ne contiennent jamais d'IBAN ni de secret (règle DomainEvent).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models import BankTransaction


def _publish(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict,
    idempotency_key: str,
    correlation_id: str | None = None,
) -> None:
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            metadata={"source": "banking_platform_v1"},
            idempotency_key=idempotency_key,
            correlation_id=uuid.UUID(correlation_id) if correlation_id else uuid.uuid4(),
        ),
    )


def _transaction_payload(tx: BankTransaction) -> dict:
    return {
        "transaction_id": tx.id,
        "external_id": tx.external_id,
        "account_id": tx.account_id,
        "booked_at": tx.booked_at,
        "value_date": getattr(tx, "value_date", None),
        "label": tx.label[:120],
        "amount": tx.amount,
        "currency": tx.currency,
        "category": tx.category,
        "status": getattr(tx, "status", "booked"),
        "source": getattr(tx, "source", "manual"),
        "counterparty_name": getattr(tx, "counterparty_name", None),
        "reference": getattr(tx, "reference", None),
        "is_duplicate": bool(getattr(tx, "is_duplicate", False)),
    }


def publish_transaction_created(
    db: Session, tx: BankTransaction, *, organization_id: int, correlation_id: str | None = None
) -> None:
    _publish(
        db,
        event_name=EventNames.BANKING_TRANSACTION_CREATED,
        organization_id=organization_id,
        aggregate_type="bank_transaction",
        aggregate_id=str(tx.id),
        payload=_transaction_payload(tx),
        idempotency_key=f"banking-tx-created-{tx.id}",
        correlation_id=correlation_id,
    )


def publish_transaction_updated(
    db: Session, tx: BankTransaction, *, organization_id: int, correlation_id: str | None = None
) -> None:
    _publish(
        db,
        event_name=EventNames.BANKING_TRANSACTION_UPDATED,
        organization_id=organization_id,
        aggregate_type="bank_transaction",
        aggregate_id=str(tx.id),
        payload=_transaction_payload(tx),
        idempotency_key=f"banking-tx-updated-{tx.account_id}-{tx.external_id}-{uuid.uuid4().hex[:8]}",
        correlation_id=correlation_id,
    )


def publish_sync_completed(
    db: Session,
    *,
    organization_id: int,
    run_id: str,
    connection_id: int,
    provider: str,
    sync_type: str,
    transactions_created: int,
    transactions_updated: int,
    duplicates_skipped: int,
    duration_ms: float | None,
    correlation_id: str | None = None,
) -> None:
    _publish(
        db,
        event_name=EventNames.BANKING_SYNC_COMPLETED,
        organization_id=organization_id,
        aggregate_type="bank_sync_run",
        aggregate_id=run_id,
        payload={
            "run_id": run_id,
            "connection_id": connection_id,
            "provider": provider,
            "sync_type": sync_type,
            "transactions_created": transactions_created,
            "transactions_updated": transactions_updated,
            "duplicates_skipped": duplicates_skipped,
            "duration_ms": duration_ms,
        },
        idempotency_key=f"banking-sync-completed-{run_id}",
        correlation_id=correlation_id,
    )


def publish_sync_failed(
    db: Session,
    *,
    organization_id: int,
    run_id: str,
    connection_id: int,
    provider: str,
    error_message: str,
    correlation_id: str | None = None,
) -> None:
    _publish(
        db,
        event_name=EventNames.BANKING_SYNC_FAILED,
        organization_id=organization_id,
        aggregate_type="bank_sync_run",
        aggregate_id=run_id,
        payload={
            "run_id": run_id,
            "connection_id": connection_id,
            "provider": provider,
            "error_message": (error_message or "")[:300],
        },
        idempotency_key=f"banking-sync-failed-{run_id}",
        correlation_id=correlation_id,
    )


def publish_connection_event(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    connection_id: int,
    provider: str,
    bank_name: str,
) -> None:
    _publish(
        db,
        event_name=event_name,
        organization_id=organization_id,
        aggregate_type="bank_connection",
        aggregate_id=str(connection_id),
        payload={
            "connection_id": connection_id,
            "provider": provider,
            "bank_name": bank_name,
        },
        idempotency_key=f"banking-conn-{event_name}-{connection_id}-{uuid.uuid4().hex[:8]}",
    )
