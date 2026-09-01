"""Filet de sécurité — connexions connected/stale à resynchroniser par lots."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection
from app.banking.banking_types import ConnectionStatus
from app.banking.consent import needs_reauth
from app.banking.errors import USER_ACTION_ERROR_CODES
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
        if needs_reauth(connection, now=moment):
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


def watch_consent_lifecycle(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Évalue l'expiration SCA et publie les événements métier (idempotents)."""
    from app.banking.banking_events import (
        publish_consent_expiring,
        publish_reauthentication_required,
    )
    from app.banking.consent import (
        consent_status,
        mark_reauth_required,
        safe_consent_log,
    )

    moment = now or datetime.utcnow()
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
    expiring = 0
    required = 0
    for connection in rows:
        status = consent_status(connection, now=moment)
        if status == "expiring" and connection.authentication_expires_at:
            publish_consent_expiring(
                db,
                organization_id=connection.organization_id,
                connection_id=connection.id,
                provider=connection.provider,
                expires_at=connection.authentication_expires_at,
            )
            safe_consent_log("banking_consent_expiring", connection)
            expiring += 1
        elif status == "reauth_required":
            reason = (connection.reauth_reason or "consent_expired")[:64]
            newly = mark_reauth_required(connection, reason=reason, now=moment)
            db.add(connection)
            publish_reauthentication_required(
                db,
                organization_id=connection.organization_id,
                connection_id=connection.id,
                provider=connection.provider,
                reason=reason,
                expires_at=connection.authentication_expires_at,
            )
            if newly:
                safe_consent_log("banking_reauth_required", connection, reason_code=reason)
            required += 1
    if required:
        db.commit()
    return {"expiring": expiring, "reauth_required": required}
