"""BillingService — orchestration plans / checkout / vues agrégées."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.billing.billing_repository import BillingRepository
from app.billing.entitlement_service import EntitlementService
from app.billing.plan_registry import list_plans, plan_to_public_dict
from app.billing.quota_service import QuotaService
from app.billing.stripe_service import StripeService
from app.billing.subscription_service import SubscriptionService
from app.billing.usage_service import UsageService
from app.config import settings


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)
        self.subscriptions = SubscriptionService(db)
        self.entitlements = EntitlementService(db)
        self.quotas = QuotaService(db)
        self.usage = UsageService(db)
        self.stripe = StripeService(db)

    def list_public_plans(self) -> list[dict[str, Any]]:
        return [plan_to_public_dict(p, include_stripe=True) for p in list_plans(public_only=True)]

    def get_subscription(self, organization_id: int, *, user=None) -> dict[str, Any]:
        return self.subscriptions.get_subscription_payload(organization_id, user=user)

    def get_entitlements(self, organization_id: int) -> dict[str, bool]:
        return self.entitlements.get_entitlements(organization_id)

    def get_quotas(self, organization_id: int) -> dict[str, Any]:
        self.subscriptions.sync_from_legacy(organization_id, rebuild=False)
        out: dict[str, Any] = {}
        for q in self.repo.list_quotas(organization_id):
            out[q.quota_code] = self.quotas.check(organization_id, q.quota_code, amount=0).model_dump(
                mode="json"
            )
        if not out:
            self.quotas.rebuild_quotas(organization_id)
            for q in self.repo.list_quotas(organization_id):
                out[q.quota_code] = self.quotas.check(organization_id, q.quota_code, amount=0).model_dump(
                    mode="json"
                )
        return out

    def get_usage(self, organization_id: int) -> dict[str, Any]:
        return self.usage.aggregate_usage(organization_id)

    def checkout(
        self,
        *,
        organization_id: int,
        user_email: str,
        plan_code: str,
        success_url: str | None = None,
        cancel_url: str | None = None,
        automatic_renewal_accepted: bool = False,
        terms_accepted: bool = False,
    ) -> dict[str, Any]:
        return self.stripe.create_checkout_session(
            organization_id=organization_id,
            user_email=user_email,
            plan_code=plan_code,
            automatic_renewal_accepted=automatic_renewal_accepted,
            terms_accepted=terms_accepted,
        )

    def customer_portal(self, organization_id: int) -> dict[str, Any]:
        return self.stripe.create_customer_portal_session(organization_id=organization_id)

    def billing_history(self, organization_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
        from app.billing.billing_models import ElfisBillingEvent

        rows = (
            self.db.query(ElfisBillingEvent)
            .filter(ElfisBillingEvent.organization_id == organization_id)
            .order_by(ElfisBillingEvent.received_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "billing_event_id": r.billing_event_id,
                "event_type": r.event_type,
                "status": r.status,
                "received_at": r.received_at.isoformat() + "Z" if r.received_at else None,
                "processed_at": r.processed_at.isoformat() + "Z" if r.processed_at else None,
                "payload_summary": r.payload_summary or {},
            }
            for r in rows
        ]

    def org_overview(self, organization_id: int, *, user=None) -> dict[str, Any]:
        """Vue org V2 — Entitlement Engine = source de vérité."""
        from app.billing.entitlement_engine import EntitlementEngine

        state = EntitlementEngine(self.db).resolve(organization_id, user=user)
        return {
            "overview": state.to_dict(),
            "plans": self.list_public_plans(),
            "history_preview": self.billing_history(organization_id, limit=10),
        }

    def platform_revenue_overview(self) -> dict[str, Any]:
        """Cockpit finance — MRR/ARR dérivés des abonnements actifs (pas Stripe live)."""
        from datetime import datetime
        from decimal import Decimal

        from app.billing.billing_models import ElfisBillingPlan, ElfisSubscription
        from app.billing.billing_types import SubscriptionStatus
        from app.billing.plan_registry import get_plan

        rows = self.db.query(ElfisSubscription).all()
        plans_by_id = {
            p.plan_id: p for p in self.db.query(ElfisBillingPlan).all()
        }
        counts = {
            "active": 0,
            "trialing": 0,
            "past_due": 0,
            "cancelled": 0,
            "suspended": 0,
            "expired": 0,
            "other": 0,
        }
        mrr = Decimal("0")
        for row in rows:
            st = (row.status or "").lower()
            if st in counts:
                counts[st] += 1
            else:
                counts["other"] += 1
            if st not in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
                continue
            amount = Decimal("0")
            interval = "month"
            db_plan = plans_by_id.get(row.plan_id)
            if db_plan is not None:
                amount = Decimal(str(db_plan.price_amount or 0))
                interval = (db_plan.billing_interval or "month").lower()
                reg = get_plan(db_plan.plan_code)
                if reg and amount == 0:
                    amount = Decimal(str(reg.price_amount or 0))
                    interval = reg.billing_interval
            if interval == "year":
                mrr += amount / 12
            else:
                mrr += amount
        arr = mrr * 12
        total = len(rows) or 1
        churn_proxy = round(100.0 * counts["cancelled"] / total, 2)
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mrr_eur": float(mrr),
            "arr_eur": float(arr),
            "subscriptions": counts,
            "subscriptions_total": len(rows),
            "churn_cancelled_ratio_pct": churn_proxy,
            "past_due": counts["past_due"],
            "trials": counts["trialing"],
            "note": (
                "MRR/ARR calculés depuis elfis_subscriptions × plans catalogue "
                "(Billing Engine). Stripe n'est pas interrogé en live."
            ),
            "source": "entitlement_engine",
        }
