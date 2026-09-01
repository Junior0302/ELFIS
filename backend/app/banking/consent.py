"""Lifecycle de consentement bancaire — état dérivé, sans secret.

status technique (connected/error/…) reste la source existante.
consent_status est calculé : valid | expiring | reauth_required | reconnecting | unknown.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from app.banking.banking_models import ElfisBankConnection
from app.banking.banking_types import ConnectionStatus, optional_provider_datetime
from app.config import settings

logger = logging.getLogger(__name__)

CONSENT_VALID = "valid"
CONSENT_EXPIRING = "expiring"
CONSENT_REAUTH_REQUIRED = "reauth_required"
CONSENT_RECONNECTING = "reconnecting"
CONSENT_UNKNOWN = "unknown"

# Codes documentés ou fail-safe (action utilisateur / Connect).
# 1010 + otp_required : SCA (doc Bridge). Autre status_code != 0 : Connect requis (doc lifecycle).
USER_ACTION_REASONS = frozenset(
    {
        "consent_expired",
        "sca_required",
        "credentials_required",
        "item_action_required",
        "connection_revoked",
    }
)
REAUTH_BLOCKING_REASONS = USER_ACTION_REASONS - {"connection_revoked"}

BRIDGE_ITEM_OK = 0
BRIDGE_ITEM_SCA = 1010  # documenté : SCA / OTP


def utcnow() -> datetime:
    return datetime.utcnow()


def warning_days() -> int:
    return max(1, int(getattr(settings, "banking_reauth_warning_days", 7) or 7))


def parse_expires_at(raw: object | None) -> datetime | None:
    return optional_provider_datetime(raw)


def classify_item_status(
    status_code: object | None,
    status_code_info: object | None = None,
) -> str | None:
    """Mappe un status_code d'item Bridge. None = OK ou inconnu (ne pas inventer)."""
    if status_code is None or status_code == "":
        return None
    try:
        code = int(status_code)
    except (TypeError, ValueError):
        return None
    if code == BRIDGE_ITEM_OK:
        return None
    info = str(status_code_info or "").strip().lower()
    if code == BRIDGE_ITEM_SCA or "otp_required" in info:
        return "sca_required"
    # Doc lifecycle : un status non-nul demande en général Bridge Connect.
    return "item_action_required"


def consent_status(connection: ElfisBankConnection, *, now: datetime | None = None) -> str:
    moment = now or utcnow()
    status = (connection.status or "").strip()
    item_id = (connection.provider_connection_id or "").strip()
    if status == ConnectionStatus.disconnected.value:
        return CONSENT_UNKNOWN
    if status == ConnectionStatus.awaiting_consent.value and item_id:
        return CONSENT_RECONNECTING
    if status in {ConnectionStatus.preparing.value, ConnectionStatus.awaiting_consent.value}:
        return CONSENT_UNKNOWN
    if needs_reauth(connection, now=moment):
        return CONSENT_REAUTH_REQUIRED
    expires = getattr(connection, "authentication_expires_at", None)
    if isinstance(expires, datetime):
        if expires <= moment:
            return CONSENT_REAUTH_REQUIRED
        if expires <= moment + timedelta(days=warning_days()):
            return CONSENT_EXPIRING
    if status == ConnectionStatus.connected.value:
        return CONSENT_VALID
    return CONSENT_UNKNOWN


def needs_reauth(connection: ElfisBankConnection, *, now: datetime | None = None) -> bool:
    """True uniquement si une action utilisateur est indispensable (pas de sync utile)."""
    moment = now or utcnow()
    if (connection.status or "") == ConnectionStatus.disconnected.value:
        return False
    reason = (getattr(connection, "reauth_reason", None) or "").strip()
    if reason in REAUTH_BLOCKING_REASONS:
        return True
    from app.banking.errors import USER_ACTION_ERROR_CODES

    code = (connection.last_sync_error_code or "").strip()
    if code in USER_ACTION_ERROR_CODES and code != "connection_revoked":
        return True
    expires = getattr(connection, "authentication_expires_at", None)
    if isinstance(expires, datetime) and expires <= moment:
        return True
    return False


def can_reauthenticate(connection: ElfisBankConnection) -> bool:
    if (connection.provider or "") != "bridge":
        return False
    if not (connection.provider_connection_id or "").strip():
        return False
    if (connection.status or "") == ConnectionStatus.disconnected.value:
        return False
    return True


def reauth_reason_for(connection: ElfisBankConnection, *, now: datetime | None = None) -> str | None:
    reason = (getattr(connection, "reauth_reason", None) or "").strip() or None
    if reason:
        return reason
    if needs_reauth(connection, now=now):
        code = (connection.last_sync_error_code or "").strip()
        if code:
            return code
        return "consent_expired"
    return None


def apply_authentication_expires_at(
    connection: ElfisBankConnection,
    raw: object | None,
    *,
    now: datetime | None = None,
) -> datetime | None:
    parsed = parse_expires_at(raw)
    if parsed is None:
        return getattr(connection, "authentication_expires_at", None)
    connection.authentication_expires_at = parsed
    moment = now or utcnow()
    if parsed > moment and (connection.reauth_reason or "") == "consent_expired":
        connection.reauth_reason = None
        connection.reauth_required_at = None
    return parsed


def mark_reauth_required(
    connection: ElfisBankConnection,
    *,
    reason: str,
    now: datetime | None = None,
) -> bool:
    """Persiste le besoin de réauth. Retourne True si c'est un nouveau signal."""
    moment = now or utcnow()
    normalized = (reason or "item_action_required")[:64]
    already = (connection.reauth_reason or "") == normalized and connection.reauth_required_at
    connection.reauth_reason = normalized
    if connection.reauth_required_at is None:
        connection.reauth_required_at = moment
    connection.updated_at = moment
    return not already


def mark_reauthenticated(
    connection: ElfisBankConnection,
    *,
    expires_at: object | None = None,
    now: datetime | None = None,
) -> None:
    moment = now or utcnow()
    connection.status = ConnectionStatus.connected.value
    connection.reauth_reason = None
    connection.reauth_required_at = None
    connection.last_reauth_at = moment
    connection.error_message = None
    from app.banking.errors import USER_ACTION_ERROR_CODES

    if (connection.last_sync_error_code or "") in USER_ACTION_ERROR_CODES:
        connection.last_sync_error_code = None
        connection.consecutive_sync_failures = 0
    apply_authentication_expires_at(connection, expires_at, now=moment)
    connection.updated_at = moment


def mark_revoked(connection: ElfisBankConnection, *, now: datetime | None = None) -> None:
    moment = now or utcnow()
    connection.status = ConnectionStatus.disconnected.value
    connection.reauth_reason = "connection_revoked"
    if connection.reauth_required_at is None:
        connection.reauth_required_at = moment
    connection.next_sync_at = None
    connection.error_message = "La connexion bancaire a été révoquée ou supprimée chez le fournisseur."
    connection.last_sync_error_code = "connection_revoked"
    connection.updated_at = moment


def apply_item_signals(
    connection: ElfisBankConnection,
    *,
    status_code: object | None = None,
    status_code_info: object | None = None,
    authentication_expires_at: object | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Met à jour expiration / action utilisateur depuis un item ou un webhook.

    Ne stocke aucun corps brut. Retourne les signaux pour logs/événements.
    """
    moment = now or utcnow()
    apply_authentication_expires_at(connection, authentication_expires_at, now=moment)
    reason = classify_item_status(status_code, status_code_info)
    newly_required = False
    if reason:
        newly_required = mark_reauth_required(connection, reason=reason, now=moment)
    elif needs_reauth(connection, now=moment) and not (connection.reauth_reason or "").strip():
        newly_required = mark_reauth_required(connection, reason="consent_expired", now=moment)
    return {
        "consent_status": consent_status(connection, now=moment),
        "needs_reauth": needs_reauth(connection, now=moment),
        "reauth_reason": reauth_reason_for(connection, now=moment),
        "newly_required": newly_required,
        "item_reason": reason,
    }


def safe_consent_log(
    event: str,
    connection: ElfisBankConnection,
    *,
    reason_code: str | None = None,
    **extra: Any,
) -> None:
    blocked = {"secret", "token", "iban", "client_secret", "authorization", "signature", "body"}
    payload = {
        "organization_id": connection.organization_id,
        "connection_id": connection.id,
        "provider": connection.provider,
        "reason_code": reason_code or connection.reauth_reason,
        "expires_at": (
            connection.authentication_expires_at.isoformat()
            if getattr(connection, "authentication_expires_at", None)
            else None
        ),
    }
    payload.update(extra)
    logger.info(event, extra={k: v for k, v in payload.items() if k.lower() not in blocked})
