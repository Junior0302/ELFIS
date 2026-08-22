"""StripeService — façade unique sur l'intégration Stripe existante.

Ne crée PAS une deuxième intégration : délègue à app.services.stripe_billing.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.billing.billing_exceptions import BillingValidationError
from app.billing.billing_security import assert_plan_purchasable, assert_webhook_size
from app.billing.plan_registry import default_plan_code
from app.billing.subscription_service import SubscriptionService
from app.config import settings


class StripeService:
    def __init__(self, db: Session):
        self.db = db

    def create_checkout_session(
        self,
        *,
        organization_id: int,
        user_email: str,
        success_url: str | None = None,
        cancel_url: str | None = None,
        plan_code: str | None = None,
        trial_period_days: int | None = None,
        automatic_renewal_accepted: bool = False,
        terms_accepted: bool = False,
    ) -> dict[str, Any]:
        code = (plan_code or default_plan_code()).strip().lower()
        # Valide que le plan est achetable ; le price_id vient du registre serveur
        price_id = assert_plan_purchasable(code)
        from app.services.stripe_billing import create_checkout_session as _create

        url, session_id = _create(
            self.db,
            organization_id=organization_id,
            customer_email=user_email,
            plan_code=code,
            trial_period_days=trial_period_days,
            price_id=price_id,
        )
        return {"url": url, "session_id": session_id, "plan_code": code}

    def create_customer_portal_session(
        self, *, organization_id: int, return_url: str | None = None
    ) -> dict[str, Any]:
        from app.services.stripe_billing import create_portal_session

        url = create_portal_session(self.db, organization_id=organization_id)
        return {"url": url}

    def get_or_create_customer(self, organization_id: int, email: str) -> str | None:
        from app.services.stripe_billing import get_organization_subscription

        sub = get_organization_subscription(self.db, organization_id)
        return sub.stripe_customer_id if sub else None

    def synchronize_subscription(self, organization_id: int) -> dict[str, Any]:
        from app.services.stripe_billing import sync_subscription_from_stripe
        from app.services.stripe_billing import get_organization_subscription

        row = get_organization_subscription(self.db, organization_id)
        if row and row.stripe_subscription_id:
            sync_subscription_from_stripe(self.db, row.stripe_subscription_id)
        SubscriptionService(self.db).sync_from_legacy(organization_id, rebuild=True)
        return {"ok": True}

    def cancel_subscription(
        self, organization_id: int, *, at_period_end: bool = True
    ) -> dict[str, Any]:
        if not at_period_end:
            raise BillingValidationError(
                "Annulation immédiate non supportée en V1 — utilisez le portail"
            )
        return self.create_customer_portal_session(organization_id=organization_id)

    def resume_subscription(self, organization_id: int) -> dict[str, Any]:
        return self.create_customer_portal_session(organization_id=organization_id)

    def change_plan(self, organization_id: int, plan_code: str) -> dict[str, Any]:
        assert_plan_purchasable(plan_code)
        return self.create_customer_portal_session(organization_id=organization_id)

    def get_subscription_status(self, organization_id: int, *, user=None) -> dict[str, Any]:
        return SubscriptionService(self.db).get_subscription_payload(organization_id, user=user)

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        assert_webhook_size(payload)
        from app.services.stripe_billing import construct_webhook_event

        return construct_webhook_event(payload, signature)

    def process_webhook_event(
        self, event: dict[str, Any], *, payload_hash: str | None = None
    ) -> dict[str, Any]:
        from app.billing.webhooks.stripe_webhook_handler import StripeWebhookHandler

        return StripeWebhookHandler(self.db).handle(event, payload_hash=payload_hash)
