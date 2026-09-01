"""Classification d'erreurs de synchronisation bancaire.

TEMPORARY  — retry / backoff BANK-4
USER_ACTION — consent / SCA / item Connect (pas de retry tempête)
CONFIGURATION — identifiants application / requête invalide (pas du consentement utilisateur)

Ne pas mapper « tout 401/403 = consent expiré ».
"""

from __future__ import annotations

from app.banking.connectors.base import ConnectorError, ConnectorNotConfiguredError

RETRYABLE_HTTP_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

ERROR_CLASS_TEMPORARY = "temporary"
ERROR_CLASS_USER_ACTION = "user_action"
ERROR_CLASS_CONFIGURATION = "configuration"
ERROR_CLASS_UNKNOWN = "unknown"

USER_ACTION_ERROR_CODES = frozenset(
    {
        "consent_expired",
        "sca_required",
        "credentials_required",
        "item_action_required",
        "connection_revoked",
    }
)
CONFIGURATION_ERROR_CODES = frozenset(
    {
        "invalid_client",
        "provider_unauthorized",
        "malformed_request",
        "invalid_credentials",
    }
)
TEMPORARY_ERROR_CODES = frozenset(
    {"timeout", "rate_limited", "provider_unavailable", "network"}
)
RETRYABLE_ERROR_CODES = TEMPORARY_ERROR_CODES


def error_class(error_code: str) -> str:
    code = (error_code or "").strip()
    if code in USER_ACTION_ERROR_CODES:
        return ERROR_CLASS_USER_ACTION
    if code in CONFIGURATION_ERROR_CODES:
        return ERROR_CLASS_CONFIGURATION
    if code in TEMPORARY_ERROR_CODES:
        return ERROR_CLASS_TEMPORARY
    return ERROR_CLASS_UNKNOWN


def classify_connector_error(error: ConnectorError | None) -> tuple[str, bool]:
    """Retourne (error_code, retryable)."""
    if error is None:
        return "unknown", False
    if isinstance(error, ConnectorNotConfiguredError):
        return "invalid_client", False

    status = error.status_code
    message = str(error).lower()
    retryable_flag = bool(error.retryable)
    item_status = getattr(error, "item_status_code", None)
    info = str(getattr(error, "provider_code", None) or "").lower()

    from app.banking.consent import classify_item_status

    item_reason = classify_item_status(item_status, info or message)
    if item_reason:
        return item_reason, False

    if status == 429 or "429" in message or "rate" in message:
        return "rate_limited", True
    if status in {408} or "timeout" in message or "délai" in message or "depasse" in message or "dépassé" in message:
        return "timeout", True
    if status is not None and status >= 500:
        return "provider_unavailable", True
    if "injoignable" in message or "network" in message or "connection reset" in message:
        return "network", True

    if "revok" in message or "disconnected" in message or "item deleted" in message:
        return "connection_revoked", False
    if "otp_required" in message or "sca" in message or "strong authentication" in message:
        return "sca_required", False
    if "consent" in message or "authentication_expires" in message:
        return "consent_expired", False
    if "invalid credential" in message or "wrong password" in message:
        return "credentials_required", False

    # 401/403 HTTP = auth application / token, pas le consentement utilisateur.
    if status in {401, 403} or "unauthorized" in message or "invalid_client" in message:
        return "provider_unauthorized", False
    if status is not None and 400 <= status < 500:
        return "malformed_request", False

    if retryable_flag:
        if status in RETRYABLE_HTTP_STATUS:
            return "provider_unavailable", True
        return "network", True
    return "unknown", False


def public_sync_error_message(error_code: str) -> str:
    if error_code in TEMPORARY_ERROR_CODES:
        return "Synchronisation temporairement indisponible. Nouvelle tentative automatique."
    if error_code == "invalid_client":
        return "Le connecteur bancaire n'est pas configuré."
    if error_code == "provider_unauthorized":
        return "Le fournisseur a refusé l'authentification de l'application."
    if error_code == "invalid_credentials":
        return "Identifiants bancaires invalides. Une reconnexion est nécessaire."
    if error_code == "credentials_required":
        return "Les identifiants bancaires doivent être renouvelés."
    if error_code == "connection_revoked":
        return "La connexion bancaire a été révoquée. Reconnectez votre banque."
    if error_code == "consent_expired":
        return "Le consentement bancaire a expiré. Une réauthentification est nécessaire."
    if error_code == "sca_required":
        return "Votre banque demande une authentification forte (SCA)."
    if error_code == "item_action_required":
        return "Une action est requise auprès de votre banque pour poursuivre la synchronisation."
    if error_code == "already_in_progress":
        return "Une synchronisation est déjà en cours."
    if error_code == "malformed_request":
        return "La demande de synchronisation a été refusée par le fournisseur."
    if error_code == "user_action_required":
        return "Une action utilisateur est requise avant de synchroniser."
    return "La synchronisation bancaire a échoué."
