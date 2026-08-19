"""Entitlement Engine V2 — source de vérité unique des droits d'organisation.

Stripe et la table legacy `subscriptions` alimentent ce moteur via sync ;
ils ne décident plus des features/quotas au runtime.

Usage :
    engine = EntitlementEngine(db)
    state = engine.resolve(organization_id)
    engine.require_feature(organization_id, FeatureCodes.AI_CLASSIFICATION, user=user)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.billing.billing_types import SubscriptionStatus
from app.billing.entitlement_service import EntitlementService
from app.billing.quota_service import QuotaService
from app.billing.subscription_service import SubscriptionService
from app.billing.usage_service import UsageService
from app.config import settings


@dataclass
class OrganizationBillingState:
    """État billing unique d'une organisation."""

    organization_id: int
    status: str
    plan_code: str
    is_trial: bool
    trial_ends_at: str | None
    trial_days_remaining: int | None
    has_product_access: bool
    read_only: bool
    entitlements: dict[str, bool]
    quotas: dict[str, Any]
    usage: dict[str, Any]
    source: str  # "entitlement_engine"
    engine_version: str
    synced_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EntitlementEngine:
    """Facade V2 — toutes les vérifications produit passent ici."""

    VERSION = "2.0.0"

    def __init__(self, db: Session):
        self.db = db
        self.subscriptions = SubscriptionService(db)
        self.entitlements = EntitlementService(db)
        self.quotas = QuotaService(db)
        self.usage = UsageService(db)

    def resolve(
        self,
        organization_id: int,
        *,
        user=None,
        now: datetime | None = None,
        rebuild: bool = False,
    ) -> OrganizationBillingState:
        now = now or datetime.utcnow()
        self.subscriptions.sync_from_legacy(organization_id, rebuild=rebuild)
        payload = self.subscriptions.get_subscription_payload(organization_id, user=user)
        status = str(payload.get("status") or SubscriptionStatus.EXPIRED)
        plan_code = str(payload.get("plan_code") or settings.elfis_default_plan_code or "starter")
        is_trial = status == SubscriptionStatus.TRIALING
        trial_ends = payload.get("trial_end") or payload.get("trial_ends_at")
        days_left = None
        if is_trial and trial_ends:
            try:
                end = datetime.fromisoformat(str(trial_ends).replace("Z", ""))
                days_left = max(0, (end - now).days)
            except ValueError:
                days_left = None

        # Accès produit : actifs / trial / past_due (grâce gérée dans entitlement_service)
        has_access = status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.PAUSED,
        }
        if status == SubscriptionStatus.SUSPENDED:
            has_access = False
        if status in {SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED}:
            has_access = bool(payload.get("access_until_period_end"))

        entitlements = self.entitlements.get_entitlements(organization_id, now=now)
        quotas_out: dict[str, Any] = {}
        for q in self.quotas.repo.list_quotas(organization_id):
            quotas_out[q.quota_code] = self.quotas.check(
                organization_id, q.quota_code, amount=0
            ).model_dump(mode="json")
        if not quotas_out:
            self.quotas.rebuild_quotas(organization_id, plan_code=plan_code)
            for q in self.quotas.repo.list_quotas(organization_id):
                quotas_out[q.quota_code] = self.quotas.check(
                    organization_id, q.quota_code, amount=0
                ).model_dump(mode="json")

        usage = self.usage.aggregate_usage(organization_id)
        read_only = status == SubscriptionStatus.PAST_DUE

        return OrganizationBillingState(
            organization_id=organization_id,
            status=status,
            plan_code=plan_code,
            is_trial=is_trial,
            trial_ends_at=str(trial_ends) if trial_ends else None,
            trial_days_remaining=days_left,
            has_product_access=has_access,
            read_only=read_only,
            entitlements=entitlements,
            quotas=quotas_out,
            usage=usage if isinstance(usage, dict) else {"items": usage},
            source="entitlement_engine",
            engine_version=self.VERSION,
            synced_at=now.isoformat() + "Z",
        )

    def check_feature(self, organization_id: int, feature_code: str, *, user=None) -> bool:
        return self.entitlements.check(organization_id, feature_code, user=user)

    def require_feature(self, organization_id: int, feature_code: str, *, user=None) -> None:
        self.entitlements.require(organization_id, feature_code, user=user)

    def check_quota(
        self, organization_id: int, quota_code: str, *, amount: int = 1
    ) -> Any:
        return self.quotas.check(organization_id, quota_code, amount=amount)

    def consume_quota(
        self, organization_id: int, quota_code: str, *, amount: int = 1
    ) -> Any:
        return self.quotas.consume(organization_id, quota_code, amount=amount)
