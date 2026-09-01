"""État de synchronisation bancaire — champs persistés sur ElfisBankConnection.

last_sync_at reste la date de dernière réussite (source de vérité existante).
L'API expose last_sync_completed_at comme alias de last_sync_at.
"""

from __future__ import annotations

from datetime import datetime

from app.banking.banking_models import ElfisBankConnection
from app.banking.errors import RETRYABLE_ERROR_CODES, USER_ACTION_ERROR_CODES

CONNECTION_SYNC_STATUSES = frozenset({"never", "queued", "syncing", "success", "failed"})


def needs_reauth(connection: ElfisBankConnection) -> bool:
    from app.banking.consent import needs_reauth as _needs_reauth

    return _needs_reauth(connection)


def mark_sync_queued(connection: ElfisBankConnection) -> None:
    if (connection.last_sync_status or "") == "syncing":
        return
    connection.last_sync_status = "queued"
    connection.updated_at = datetime.utcnow()


def mark_sync_started(connection: ElfisBankConnection) -> None:
    now = datetime.utcnow()
    connection.last_sync_started_at = now
    connection.last_sync_status = "syncing"
    connection.updated_at = now


def mark_sync_success(connection: ElfisBankConnection) -> None:
    now = datetime.utcnow()
    connection.last_sync_at = now
    connection.last_sync_status = "success"
    connection.last_sync_error_code = None
    connection.consecutive_sync_failures = 0
    connection.error_message = None
    connection.updated_at = now


def mark_sync_failed(
    connection: ElfisBankConnection,
    *,
    error_code: str,
    public_message: str | None = None,
) -> None:
    now = datetime.utcnow()
    connection.last_sync_status = "failed"
    connection.last_sync_error_code = (error_code or "unknown")[:64]
    connection.consecutive_sync_failures = int(connection.consecutive_sync_failures or 0) + 1
    if public_message:
        connection.error_message = public_message[:500]
    connection.updated_at = now
