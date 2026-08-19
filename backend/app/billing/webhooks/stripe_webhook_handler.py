"""Handler webhook Stripe — idempotence + sync entitlements/quotas."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing.billing_logging import safe_billing_log_context, sanitize_billing_error
from app.billing.billing_repository import BillingRepository
from app.billing.billing_security import hash_payload, summarize_webhook_payload
from app.billing.billing_types import BillingEventStatus
from app.billing.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class StripeWebhookHandler:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)

    def handle(self, event: dict[str, Any], *, payload_hash: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        provider_event_id = str(event.get("id") or "")
        event_type = str(event.get("type") or "")

        if provider_event_id:
            existing = self.repo.get_event_by_provider_id(provider_event_id)
            if existing and existing.status == BillingEventStatus.PROCESSED:
                logger.info(
                    "billing_webhook_idempotent",
                    extra=safe_billing_log_context(
                        provider_event_id=provider_event_id,
                        event_type=event_type,
                        idempotent_reuse=True,
                    ),
                )
                return {"ok": True, "idempotent": True, "billing_event_id": existing.billing_event_id}

        summary = summarize_webhook_payload(event)
        org_id = self._extract_organization_id(event)
        row = None
        try:
            row = self.repo.create_event(
                provider="stripe",
                provider_event_id=provider_event_id or None,
                event_type=event_type,
                organization_id=org_id,
                payload_hash=payload_hash,
                payload_summary=summary,
            )
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = self.repo.get_event_by_provider_id(provider_event_id) if provider_event_id else None
            if existing and existing.status == BillingEventStatus.PROCESSED:
                return {"ok": True, "idempotent": True, "billing_event_id": existing.billing_event_id}
            # Concurrent claim : l'autre worker traite déjà l'événement — ne pas ré-appliquer.
            if existing and existing.status == BillingEventStatus.RECEIVED:
                return {
                    "ok": True,
                    "idempotent": True,
                    "in_progress": True,
                    "billing_event_id": existing.billing_event_id,
                }
            row = existing

        try:
            # apply_stripe=True : flux complet (tests / StripeService).
            # En production le router legacy appelle apply puis post_process_legacy_webhook.
            if getattr(self, "_apply_stripe", True):
                from app.services.stripe_billing import apply_webhook_event

                apply_webhook_event(self.db, event)

            if org_id is None:
                org_id = self._extract_organization_id(event)
            if org_id:
                sub = SubscriptionService(self.db).sync_from_legacy(org_id, rebuild=True)
                if row and sub:
                    row.organization_id = org_id
                    row.subscription_id = sub.subscription_id
                self._publish_and_notify(event_type, org_id, sub)

            if row:
                self.repo.mark_event_processed(row)
            self.db.commit()
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.info(
                "billing_webhook_processed",
                extra=safe_billing_log_context(
                    billing_event_id=row.billing_event_id if row else None,
                    provider_event_id=provider_event_id,
                    organization_id=org_id,
                    event_type=event_type,
                    processing_time_ms=elapsed,
                ),
            )
            return {
                "ok": True,
                "idempotent": False,
                "billing_event_id": row.billing_event_id if row else None,
            }
        except Exception as exc:
            if row:
                self.repo.mark_event_failed(row, sanitize_billing_error(str(exc)) or "error")
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
            logger.exception(
                "billing_webhook_failed",
                extra=safe_billing_log_context(
                    provider_event_id=provider_event_id,
                    event_type=event_type,
                    organization_id=org_id,
                ),
            )
            raise

    def _extract_organization_id(self, event: dict[str, Any]) -> int | None:
        obj = (event.get("data") or {}).get("object") or {}
        meta = obj.get("metadata") or {}
        raw = meta.get("organization_id")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
        # Fallback via customer / subscription Stripe IDs
        from app.models_saas import Subscription

        cust = obj.get("customer")
        sub_id = obj.get("id") if obj.get("object") == "subscription" else obj.get("subscription")
        if sub_id:
            row = (
                self.db.query(Subscription)
                .filter(Subscription.stripe_subscription_id == sub_id)
                .first()
            )
            if row:
                return row.organization_id
        if cust:
            row = (
                self.db.query(Subscription)
                .filter(Subscription.stripe_customer_id == cust)
                .first()
            )
            if row:
                return row.organization_id
        return None

    def _publish_and_notify(self, event_type: str, organization_id: int, sub) -> None:
        try:
            from app.billing.billing_events import publish_billing_event_for_stripe

            publish_billing_event_for_stripe(
                self.db,
                stripe_event_type=event_type,
                organization_id=organization_id,
                subscription=sub,
            )
        except Exception:
            logger.exception("billing_publish_failed org=%s", organization_id)
