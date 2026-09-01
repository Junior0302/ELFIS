"""Webhook Bridge API (bridgeapi.io) — signature HMAC-SHA256, raw body, fail closed.

Documentation officielle :
https://docs.bridgeapi.io/docs/secure-your-webhooks

- Header : ``BridgeApi-Signature``
- Schéma live unique : ``v1=<hex HMAC-SHA256 uppercase>``
- Message : corps brut (bytes) ; ne pas re-sérialiser le JSON
- Rotation : jusqu'à 2 secrets (actuel + précédent, 24 h)
- Ne pas confondre avec bridge.xyz (RSA / X-Webhook-Signature)

Dépendances encore Production Bridge (non activées ici) :
- secret webhook créé dans le dashboard Bridge (affiché une seule fois)
- URL callback HTTPS enregistrée : POST /api/banking/connectors/bridge/webhook
- événements item.refreshed / accounts souscrits côté dashboard
- workers Job Queue pour consommer les jobs enqueued
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.banking.banking_models import ElfisBankConnection, ElfisBankWebhookReceipt
from app.banking.sync_jobs import enqueue_connection_sync
from app.config import settings
from app.observability.metrics import metrics_registry

logger = logging.getLogger(__name__)

BRIDGE_SIGNATURE_HEADER = "bridgeapi-signature"
BRIDGE_PROVIDER = "bridge"
# BANK-4 : ces types enqueuent banking.sync_connection.v1 si pas de reauth requis
SYNC_EVENT_TYPES = frozenset(
    {
        "item.refreshed",
        "item.account.updated",
    }
)
LIFECYCLE_EVENT_TYPES = frozenset(
    {
        "item.deleted",
        "item.created",
        "item.account.created",
        "item.account.deleted",
        "user.deleted",
        "TEST_EVENT",
    }
)
# Parsables / ignorés proprement après signature + receipt (jamais 500).
KNOWN_IGNORED_EVENT_TYPES = LIFECYCLE_EVENT_TYPES


class BridgeWebhookError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 401):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _webhook_secrets() -> list[str]:
    secrets = []
    for raw in (
        settings.banking_bridge_webhook_secret,
        settings.banking_bridge_webhook_secret_previous,
    ):
        value = (raw or "").strip().strip('"').strip("'")
        if value and value not in secrets:
            secrets.append(value)
    return secrets


def extract_v1_signatures(header: str | None) -> list[str]:
    if not header:
        return []
    found: list[str] = []
    for part in header.split(","):
        item = part.strip()
        if not item.startswith("v1="):
            continue
        value = item.split("=", 1)[1].strip().upper()
        if value:
            found.append(value)
    return found


def expected_signature(secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest().upper()


def verify_bridge_signature(raw_body: bytes, header: str | None, *, secrets: list[str] | None = None) -> bool:
    active = secrets if secrets is not None else _webhook_secrets()
    if not active:
        return False
    presented = extract_v1_signatures(header)
    if not presented:
        return False
    for secret in active:
        expected = expected_signature(secret, raw_body)
        for candidate in presented:
            if hmac.compare_digest(expected, candidate):
                return True
    return False


def payload_hash(raw_body: bytes) -> str:
    """Digest SHA-256 du corps brut — seul identifiant d'événement persisté."""
    return hashlib.sha256(raw_body).hexdigest()


def provider_event_id_from_body(raw_body: bytes) -> str:
    """Bridge v2025 ne documente pas d'event_id unique.

    Interdit : payload['id'], uuid4(), item_id seul, Set mémoire.
    ID déterministe = sha256(raw_body).hexdigest() (64 hex).
    """
    return payload_hash(raw_body)


def _safe_log(event: str, **extra: Any) -> None:
    blocked = {"secret", "token", "iban", "client_secret", "authorization", "signature", "body"}
    logger.info(event, extra={k: v for k, v in extra.items() if k.lower() not in blocked})


def _lookup_connection(db: Session, item_id: str) -> ElfisBankConnection | None:
    if not item_id:
        return None
    matches = (
        db.query(ElfisBankConnection)
        .filter(
            ElfisBankConnection.provider == BRIDGE_PROVIDER,
            ElfisBankConnection.provider_connection_id == item_id,
        )
        .all()
    )
    if len(matches) != 1:
        return None
    return matches[0]


def ingest_bridge_webhook(
    db: Session,
    *,
    raw_body: bytes,
    signature_header: str | None,
) -> dict[str, Any]:
    max_bytes = max(1024, int(settings.banking_webhook_max_bytes))
    if len(raw_body) > max_bytes:
        metrics_registry.incr("elfis_banking_webhook_rejected_total", labels={"reason": "too_large"})
        raise BridgeWebhookError("payload_too_large", "Webhook trop volumineux.", status_code=413)

    secrets = _webhook_secrets()
    if not secrets:
        metrics_registry.incr("elfis_banking_webhook_rejected_total", labels={"reason": "not_configured"})
        _safe_log("banking_webhook_rejected", provider=BRIDGE_PROVIDER, reason="not_configured")
        raise BridgeWebhookError(
            "webhook_not_configured",
            "Webhook Bridge non configuré.",
            status_code=503,
        )

    if not verify_bridge_signature(raw_body, signature_header, secrets=secrets):
        metrics_registry.incr("elfis_banking_webhook_rejected_total", labels={"reason": "invalid_signature"})
        _safe_log("banking_webhook_rejected", provider=BRIDGE_PROVIDER, reason="invalid_signature")
        raise BridgeWebhookError("invalid_signature", "Signature webhook invalide.", status_code=401)

    try:
        parsed = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        metrics_registry.incr("elfis_banking_webhook_rejected_total", labels={"reason": "malformed"})
        raise BridgeWebhookError("malformed", "Corps webhook illisible.", status_code=400) from exc

    if not isinstance(parsed, dict):
        raise BridgeWebhookError("malformed", "Corps webhook illisible.", status_code=400)

    event_type = str(parsed.get("type") or "").strip()
    content = parsed.get("content") if isinstance(parsed.get("content"), dict) else {}
    event_id = provider_event_id_from_body(raw_body)
    digest = event_id
    # Connexion toujours via item_id Bridge — jamais account_id seul.
    item_id = str(content.get("item_id") or "").strip()

    _safe_log(
        "banking_webhook_received",
        provider=BRIDGE_PROVIDER,
        event_type=event_type,
        connection_id=None,
        organization_id=None,
    )

    receipt = ElfisBankWebhookReceipt(
        provider=BRIDGE_PROVIDER,
        provider_event_id=event_id,
        event_type=event_type[:128],
        payload_hash=digest,
        status="received",
    )
    try:
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(ElfisBankWebhookReceipt)
            .filter(
                ElfisBankWebhookReceipt.provider == BRIDGE_PROVIDER,
                ElfisBankWebhookReceipt.provider_event_id == event_id,
            )
            .one_or_none()
        )
        if existing and not _receipt_needs_job(existing):
            _safe_log(
                "banking_webhook_duplicate",
                provider=BRIDGE_PROVIDER,
                event_type=event_type,
                organization_id=existing.organization_id,
                connection_id=existing.connection_id,
            )
            return {
                "ok": True,
                "duplicate": True,
                "ignored": existing.status == "ignored",
                "receipt_id": existing.id,
                "job_id": existing.job_id,
            }
        receipt = existing
        if receipt is None:
            raise BridgeWebhookError("malformed", "Réception webhook incohérente.", status_code=500)

    return _enqueue_from_receipt(
        db,
        receipt=receipt,
        event_type=event_type,
        item_id=item_id,
        event_id=event_id,
        content=content,
    )


def _receipt_needs_job(receipt: ElfisBankWebhookReceipt) -> bool:
    """Une receipt 'received' (crash avant enqueue) ne doit pas bloquer le retry."""
    if receipt.status == "ignored":
        return False
    if receipt.status == "queued" and (receipt.job_id or "").strip():
        return False
    return True


def _apply_webhook_lifecycle(
    db: Session,
    connection: ElfisBankConnection | None,
    *,
    event_type: str,
    content: dict[str, Any],
) -> None:
    from app.banking.banking_events import (
        publish_consent_expiring,
        publish_connection_revoked,
        publish_reauthentication_required,
    )
    from app.banking.consent import (
        apply_item_signals,
        mark_revoked,
        needs_reauth,
        safe_consent_log,
    )

    if connection is None:
        return
    if event_type == "item.deleted":
        mark_revoked(connection)
        db.add(connection)
        publish_connection_revoked(
            db,
            organization_id=connection.organization_id,
            connection_id=connection.id,
            provider=connection.provider,
            bank_name=connection.bank_name,
        )
        safe_consent_log("banking_connection_revoked", connection, reason_code="connection_revoked")
        return
    if event_type not in SYNC_EVENT_TYPES:
        return
    signals = apply_item_signals(
        connection,
        status_code=content.get("status_code"),
        status_code_info=content.get("status_code_info"),
        authentication_expires_at=content.get("authentication_expires_at"),
    )
    db.add(connection)
    status = signals["consent_status"]
    if status == "expiring" and connection.authentication_expires_at:
        publish_consent_expiring(
            db,
            organization_id=connection.organization_id,
            connection_id=connection.id,
            provider=connection.provider,
            expires_at=connection.authentication_expires_at,
        )
        safe_consent_log("banking_consent_expiring", connection)
    if needs_reauth(connection):
        if signals.get("newly_required"):
            publish_reauthentication_required(
                db,
                organization_id=connection.organization_id,
                connection_id=connection.id,
                provider=connection.provider,
                reason=signals["reauth_reason"] or "consent_expired",
                expires_at=connection.authentication_expires_at,
            )
        safe_consent_log(
            "banking_reauth_required",
            connection,
            reason_code=signals["reauth_reason"],
        )


def _enqueue_from_receipt(
    db: Session,
    *,
    receipt: ElfisBankWebhookReceipt,
    event_type: str,
    item_id: str,
    event_id: str,
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from app.banking.consent import needs_reauth

    payload = content if isinstance(content, dict) else {}
    connection = _lookup_connection(db, item_id)
    _apply_webhook_lifecycle(db, connection, event_type=event_type, content=payload)

    if event_type not in SYNC_EVENT_TYPES or connection is None:
        receipt.status = "ignored"
        if connection is not None:
            receipt.organization_id = connection.organization_id
            receipt.connection_id = connection.id
        db.add(receipt)
        db.commit()
        return {
            "ok": True,
            "ignored": True,
            "receipt_id": receipt.id,
            "event_type": event_type,
        }

    if needs_reauth(connection):
        receipt.status = "ignored"
        receipt.organization_id = connection.organization_id
        receipt.connection_id = connection.id
        db.add(receipt)
        db.commit()
        return {
            "ok": True,
            "ignored": True,
            "user_action_required": True,
            "receipt_id": receipt.id,
            "event_type": event_type,
        }

    try:
        result = enqueue_connection_sync(
            db,
            organization_id=connection.organization_id,
            connection_id=connection.id,
            trigger="webhook",
            idempotency_key=f"banking-sync-webhook-{event_id}",
            provider=connection.provider,
        )
    except Exception as exc:
        from app.banking.sync_jobs import BankingSyncEnqueueError

        if isinstance(exc, BankingSyncEnqueueError):
            receipt.status = "ignored"
            receipt.organization_id = connection.organization_id
            receipt.connection_id = connection.id
            db.add(receipt)
            db.commit()
            return {
                "ok": True,
                "ignored": True,
                "user_action_required": True,
                "receipt_id": receipt.id,
                "event_type": event_type,
            }
        db.rollback()
        raise

    receipt.status = "queued"
    receipt.organization_id = connection.organization_id
    receipt.connection_id = connection.id
    receipt.job_id = result.job_id
    db.add(receipt)
    db.commit()
    return {
        "ok": True,
        "queued": True,
        "duplicate": bool(result.idempotent_reuse),
        "receipt_id": receipt.id,
        "job_id": result.job_id,
    }
