"""Classification d'erreurs de synchronisation bancaire — retryable vs permanent."""

from __future__ import annotations

from app.banking.connectors.base import ConnectorError, ConnectorNotConfiguredError

RETRYABLE_HTTP_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
# 409 fournisseur (ex. user already exists) n'est pas BANK-3.1. BANK-3.1
# already_in_progress est géré à part et n'entre pas dans cette table.


def classify_connector_error(error: ConnectorError | None) -> tuple[str, bool]:
    """Retourne (error_code, retryable)."""
    if error is None:
        return "unknown", False
    if isinstance(error, ConnectorNotConfiguredError):
        return "invalid_credentials", False

    status = error.status_code
    message = str(error).lower()
    retryable_flag = bool(error.retryable)

    if status == 429 or "429" in message or "rate" in message:
        return "rate_limited", True
    if status in {408} or "timeout" in message or "délai" in message or "depasse" in message or "dépassé" in message:
        return "timeout", True
    if status is not None and status >= 500:
        return "provider_unavailable", True
    if "injoignable" in message or "network" in message or "connection reset" in message:
        return "network", True

    if status in {401, 403} or "unauthorized" in message or "invalid_client" in message:
        return "invalid_credentials", False
    if "revok" in message or "disconnected" in message:
        return "connection_revoked", False
    if (
        "consent" in message
        or "sca" in message
        or "expired" in message
        or "authentication_expires" in message
    ):
        return "consent_expired", False
    if status is not None and 400 <= status < 500:
        return "malformed_request", False

    if retryable_flag:
        if status in RETRYABLE_HTTP_STATUS:
            return "provider_unavailable", True
        return "network", True
    return "unknown", False


def public_sync_error_message(error_code: str) -> str:
    if error_code in {"timeout", "rate_limited", "provider_unavailable", "network"}:
        return "Synchronisation temporairement indisponible. Nouvelle tentative automatique."
    if error_code == "invalid_credentials":
        return "Identifiants bancaires invalides. Une reconnexion est nécessaire."
    if error_code == "connection_revoked":
        return "La connexion bancaire a été révoquée. Reconnectez votre banque."
    if error_code == "consent_expired":
        return "Le consentement bancaire a expiré. Une réauthentification est nécessaire."
    if error_code == "already_in_progress":
        return "Une synchronisation est déjà en cours."
    if error_code == "malformed_request":
        return "La demande de synchronisation a été refusée par le fournisseur."
    return "La synchronisation bancaire a échoué."
