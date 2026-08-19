"""SubscriptionService — sync abonnement org ↔ tables Billing."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.billing.billing_models import ElfisSubscription
from app.billing.billing_repository import BillingRepository
from app.billing.billing_types import STRIPE_STATUS_MAP, SubscriptionStatus
from app.billing.entitlement_service import EntitlementService
from app.billing.plan_registry import (
    default_plan_code,
    get_plan,
    plan_code_for_stripe_price,
    plan_to_public_dict,
)
from app.billing.quota_service import QuotaService
from app.config import settings


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)

    def past_due_grace_days(self) -> int:
        return int(
            getattr(settings, "elfis_billing_past_due_grace_days", None)
            or settings.stripe_past_due_grace_days
            or 7
        )

    def map_stripe_status(self, stripe_status: str | None) -> str:
        if not stripe_status:
            return SubscriptionStatus.INCOMPLETE
        return STRIPE_STATUS_MAP.get(stripe_status, stripe_status)

    def ensure_plan_row(self, plan_code: str) -> str:
        """Retourne plan_id (UUID métier) pour un plan_code."""
        from decimal import Decimal

        plan = get_plan(plan_code) or get_plan(default_plan_code())
        assert plan is not None
        row = self.repo.get_plan_by_code(plan.plan_code)
        if not row:
            from app.billing.plan_registry import resolve_stripe_price_id

            row = self.repo.upsert_plan_row(
                plan_code=plan.plan_code,
                name=plan.name,
                description=plan.description,
                currency=plan.currency,
                price_amount=Decimal(plan.price_amount),
                billing_interval=plan.billing_interval,
                trial_days=plan.trial_days,
                stripe_price_id=resolve_stripe_price_id(plan.plan_code),
                is_active=plan.is_active,
                is_public=plan.is_public,
                features=dict(plan.features),
                quotas=dict(plan.quotas),
            )
            self.db.flush()
        return row.plan_id

    def sync_from_legacy(
        self,
        organization_id: int,
        *,
        user_id: int | None = None,
        rebuild: bool = True,
    ) -> ElfisSubscription | None:
        """Synchronise elfis_subscriptions depuis la table legacy subscriptions."""
        from app.models_saas import Subscription as LegacySubscription

        legacy = (
            self.db.query(LegacySubscription)
            .filter(LegacySubscription.organization_id == organization_id)
            .order_by(LegacySubscription.id.desc())
            .all()
        )
        if not legacy:
            return None
        row = None
        for status in ("trialing", "active", "past_due", "unpaid", "paused", "incomplete"):
            for candidate in legacy:
                if candidate.status == status:
                    row = candidate
                    break
            if row:
                break
        if row is None:
            row = next((c for c in legacy if c.stripe_subscription_id), legacy[0])
        legacy = row

        plan_code = (
            plan_code_for_stripe_price(legacy.stripe_price_id)
            or default_plan_code()
        )
        plan_id = self.ensure_plan_row(plan_code)
        status = self.map_stripe_status(legacy.status)
        if legacy.admin_revoked_at:
            status = SubscriptionStatus.SUSPENDED

        current = self.repo.get_current_subscription(organization_id)
        now = datetime.utcnow()
        grace_ends = None
        payment_failed = legacy.last_payment_failure_at or legacy.past_due_since
        if status == SubscriptionStatus.PAST_DUE and payment_failed:
            grace_ends = payment_failed + timedelta(days=self.past_due_grace_days())

        if not current:
            current = ElfisSubscription(
                id=str(uuid4()),
                subscription_id=str(uuid4()),
                organization_id=organization_id,
                plan_id=plan_id,
                status=status,
                source="stripe",
                is_current=True,
                created_at=now,
            )
            self.db.add(current)
        else:
            self.repo.mark_others_not_current(organization_id, keep_id=current.subscription_id)

        current.plan_id = plan_id
        current.status = status
        current.legacy_subscription_id = legacy.id
        current.stripe_customer_id = legacy.stripe_customer_id
        current.stripe_subscription_id = legacy.stripe_subscription_id
        current.stripe_price_id = legacy.stripe_price_id
        current.trial_started_at = legacy.trial_start
        current.trial_ends_at = legacy.trial_end
        current.current_period_started_at = legacy.current_period_start
        current.current_period_ends_at = legacy.current_period_end
        current.cancel_at_period_end = bool(legacy.cancel_at_period_end)
        current.cancelled_at = legacy.canceled_at
        current.ended_at = legacy.access_ends_at if status in (
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
        ) else None
        current.payment_failed_at = payment_failed
        current.grace_period_ends_at = grace_ends
        current.is_current = True
        current.updated_by_user_id = user_id
        current.updated_at = now
        self.db.flush()

        if rebuild:
            EntitlementService(self.db).rebuild_entitlements(
                organization_id,
                subscription_id=current.subscription_id,
                plan_code=plan_code,
            )
            QuotaService(self.db).rebuild_quotas(
                organization_id,
                plan_code=plan_code,
                subscription_id=current.subscription_id,
            )
        return current

    def get_subscription_payload(
        self, organization_id: int, *, user=None
    ) -> dict[str, Any]:
        from app.billing.usage_service import UsageService
        from app.subscriptions.access import get_subscription_access, serialize_access

        self.sync_from_legacy(organization_id, rebuild=False)
        sub = self.repo.get_current_subscription(organization_id)
        access = get_subscription_access(self.db, organization_id, user=user)
        plan_code = plan_code_for_stripe_price(sub.stripe_price_id if sub else None) or default_plan_code()
        plan = get_plan(plan_code)
        trial_days = int(getattr(settings, "elfis_trial_days", None) or settings.stripe_trial_days or 14)

        will_renew = bool(
            access.has_access
            and not access.cancel_at_period_end
            and access.subscription_status in ("trialing", "active", "past_due")
        )
        next_billing = access.next_billing_at or access.current_period_ends_at or access.trial_ends_at

        entitlements = EntitlementService(self.db).get_entitlements(organization_id)
        qs = QuotaService(self.db)
        if not self.repo.list_quotas(organization_id):
            qs.rebuild_quotas(organization_id, plan_code=plan_code)
        quotas: dict[str, Any] = {}
        for q in self.repo.list_quotas(organization_id):
            quotas[q.quota_code] = qs.check(organization_id, q.quota_code, amount=0).model_dump(
                mode="json"
            )
        usage = UsageService(self.db).aggregate_usage(organization_id)

        return {
            "subscription_id": sub.subscription_id if sub else None,
            "legacy_subscription_id": sub.legacy_subscription_id if sub else None,
            "plan": plan_to_public_dict(plan) if plan else {"code": plan_code},
            "plan_code": plan_code,
            "status": access.subscription_status,
            "raw_status": access.raw_status,
            "trial_days": trial_days,
            "trial_ends_at": access.trial_ends_at.isoformat() + "Z" if access.trial_ends_at else None,
            "trial_started_at": access.trial_started_at.isoformat() + "Z" if access.trial_started_at else None,
            "current_period_ends_at": (
                access.current_period_ends_at.isoformat() + "Z" if access.current_period_ends_at else None
            ),
            "cancel_at_period_end": access.cancel_at_period_end,
            "will_renew_automatically": will_renew,
            "next_billing_date": next_billing.isoformat() + "Z" if next_billing else None,
            "price": float(plan.price_amount) if plan else 19.0,
            "currency": plan.currency if plan else "EUR",
            "grace_period_ends_at": (
                sub.grace_period_ends_at.isoformat() + "Z" if sub and sub.grace_period_ends_at else None
            ),
            "entitlements": entitlements,
            "quotas": quotas,
            "usage": usage,
            "access": serialize_access(access),
            "disclosure": {
                "trial": f"Essai gratuit de {trial_days} jours, puis 19 €/mois.",
                "renewal": "Renouvellement automatique. Annulation possible avant la fin de l’essai.",
            },
        }

    def suspend(self, subscription_id: str, *, user_id: int | None = None) -> ElfisSubscription:
        row = self.repo.get_subscription_by_id(subscription_id)
        if not row:
            from app.billing.billing_exceptions import BillingNotFoundError

            raise BillingNotFoundError("Abonnement introuvable")
        row.status = SubscriptionStatus.SUSPENDED
        row.updated_by_user_id = user_id
        row.updated_at = datetime.utcnow()
        # Legacy mirror
        if row.legacy_subscription_id:
            from app.models_saas import Subscription

            legacy = self.db.get(Subscription, row.legacy_subscription_id)
            if legacy:
                legacy.admin_revoked_at = datetime.utcnow()
                legacy.admin_revoked_by = user_id
        EntitlementService(self.db).rebuild_entitlements(
            row.organization_id, subscription_id=row.subscription_id
        )
        from app.billing.billing_events import publish_billing_domain_event
        from app.events.event_types import EventNames

        publish_billing_domain_event(
            self.db,
            EventNames.BILLING_SUBSCRIPTION_SUSPENDED,
            row.organization_id,
            row,
        )
        self.db.flush()
        return row

    def restore(self, subscription_id: str, *, user_id: int | None = None) -> ElfisSubscription:
        row = self.repo.get_subscription_by_id(subscription_id)
        if not row:
            from app.billing.billing_exceptions import BillingNotFoundError

            raise BillingNotFoundError("Abonnement introuvable")
        if row.legacy_subscription_id:
            from app.models_saas import Subscription

            legacy = self.db.get(Subscription, row.legacy_subscription_id)
            if legacy:
                legacy.admin_revoked_at = None
                legacy.admin_revoked_by = None
                legacy.admin_revoked_reason_public = ""
        synced = self.sync_from_legacy(row.organization_id, user_id=user_id, rebuild=True)
        from app.billing.billing_events import publish_billing_domain_event
        from app.events.event_types import EventNames

        target = synced or row
        publish_billing_domain_event(
            self.db,
            EventNames.BILLING_SUBSCRIPTION_REACTIVATED,
            target.organization_id,
            target,
        )
        return target
