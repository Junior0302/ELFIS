"""Filet de sécurité — connexions connected/stale à resynchroniser par lots."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection
from app.banking.banking_types import ConnectionStatus
from app.banking.sync_status import USER_ACTION_ERROR_CODES
from app.config import settings


def _stale_cutoff(now: datetime, stale_hours: int) -> datetime:
    return now - timedelta(hours=max(1, stale_hours))


def select_stale_connections(
    db: Session,
    *,
    now: datetime | None = None,
    stale_hours: int | None = None,
    limit: int | None = None,
) -> list[ElfisBankConnection]:
    """Connexions éligibles : connected (ou erreur retryable), stale, pas syncing."""
    moment = now or datetime.utcnow()
    hours = stale_hours if stale_hours is not None else int(settings.banking_sync_stale_hours)
    batch = limit if limit is not None else int(settings.banking_sync_sweep_batch_size)
    batch = max(1, min(batch, 100))
    cutoff = _stale_cutoff(moment, hours)

    rows = (
        db.query(ElfisBankConnection)
        .filter(
            ElfisBankConnection.provider_connection_id != "",
            ElfisBankConnection.status.in_(
                [ConnectionStatus.connected.value, ConnectionStatus.error.value]
            ),
        )
        .all()
    )
    rows.sort(key=lambda c: (c.last_sync_at is not None, c.last_sync_at or moment, c.id))
    eligible: list[ElfisBankConnection] = []
    for connection in rows:
        if (connection.last_sync_status or "") == "syncing":
            continue
        if (connection.last_sync_error_code or "") in USER_ACTION_ERROR_CODES:
            continue
        if connection.status == ConnectionStatus.error.value:
            code = (connection.last_sync_error_code or "").strip()
            if code and code not in {"timeout", "rate_limited", "provider_unavailable", "network", "unknown", ""}:
                continue
        next_due = connection.next_sync_at
        last_done = connection.last_sync_at
        stale = False
        if next_due is not None and next_due <= moment:
            stale = True
        elif last_done is None:
            stale = True
        elif last_done <= cutoff:
            stale = True
        if not stale:
            continue
        eligible.append(connection)
        if len(eligible) >= batch:
            break
    return eligible
