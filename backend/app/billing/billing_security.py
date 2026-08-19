"""Sécurité Billing — signature Stripe, validation price_id, taille webhook."""

from __future__ import annotations

import hashlib
from typing import Any

from app.billing.billing_exceptions import BillingValidationError, StripeWebhookError
from app.billing.plan_registry import plan_code_for_stripe_price, resolve_stripe_price_id
from app.config import settings


def max_webhook_bytes() -> int:
    return int(getattr(settings, "elfis_billing_webhook_max_bytes", 1_048_576) or 1_048_576)


def assert_webhook_size(payload: bytes) -> None:
    if len(payload) > max_webhook_bytes():
        raise StripeWebhookError("Webhook trop volumineux")


def hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def assert_known_price_id(price_id: str | None) -> str:
    """Refuse tout price_id non mappé à un plan connu."""
    if not price_id or not str(price_id).strip():
        raise BillingValidationError("Identifiant tarif inconnu")
    code = plan_code_for_stripe_price(price_id.strip())
    if not code:
        raise BillingValidationError("Identifiant tarif non autorisé")
    return code


def assert_plan_purchasable(plan_code: str) -> str:
    price = resolve_stripe_price_id(plan_code)
    if not price:
        raise BillingValidationError("Plan non achetable ou tarif Stripe non configuré")
    return price


def sanitize_stripe_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    if not metadata:
        return {}
    allowed = {"organization_id", "plan_code", "user_id", "correlation_id"}
    out: dict[str, str] = {}
    for key, value in metadata.items():
        if key not in allowed:
            continue
        text = str(value).strip()[:128]
        if text:
            out[key] = text
    return out


def summarize_webhook_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Résumé non sensible — jamais de carte / CVC / secret."""
    data_obj = (event.get("data") or {}).get("object") or {}
    return {
        "type": event.get("type"),
        "object": data_obj.get("object"),
        "id": data_obj.get("id"),
        "customer": data_obj.get("customer"),
        "status": data_obj.get("status"),
        "subscription": data_obj.get("subscription"),
        "metadata_keys": sorted(list((data_obj.get("metadata") or {}).keys()))[:20],
    }


def redact_secrets_from_text(text: str) -> str:
    from app.billing.billing_logging import sanitize_billing_error

    return sanitize_billing_error(text) or ""
