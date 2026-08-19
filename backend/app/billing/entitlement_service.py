"""EntitlementService — résolution des droits fonctionnels."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.billing.billing_exceptions import FeatureNotAvailableError
from app.billing.billing_models import ElfisEntitlement
from app.billing.billing_repository import BillingRepository
from app.billing.billing_types import (
    COSTLY_FEATURES_WHEN_SUSPENDED,
    EntitlementSources,
    READ_FEATURES,
    SubscriptionStatus,
)
from app.billing.plan_registry import get_plan
from app.config import settings


class EntitlementService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)

    def _billing_enabled(self) -> bool:
        return bool(getattr(settings, "elfis_billing_enabled", True))

    def _enforce(self) -> bool:
        return bool(getattr(settings, "elfis_billing_enforce_entitlements", True))

    def check(
        self,
        organization_id: int,
        feature_code: str,
        *,
        now: datetime | None = None,
        user=None,
    ) -> bool:
        try:
            self.require(organization_id, feature_code, now=now, user=user)
            return True
        except FeatureNotAvailableError:
            return False

    def require(
        self,
        organization_id: int,
        feature_code: str,
        *,
        now: datetime | None = None,
        user=None,
    ) -> None:
        if not self._billing_enabled() or not self._enforce():
            return
        # Bypass plateforme
        if user is not None:
            from app.subscriptions.access import _platform_bypass

            if _platform_bypass(user):
                return

        now = now or datetime.utcnow()
        resolved = self._resolve(organization_id, feature_code, now=now)
        if not resolved:
            raise FeatureNotAvailableError(feature_code)

    def get_entitlements(self, organization_id: int, *, now: datetime | None = None) -> dict[str, bool]:
        now = now or datetime.utcnow()
        plan = self._effective_plan_features(organization_id)
        result = dict(plan)
        for row in self.repo.list_entitlements(organization_id):
            if row.source in (EntitlementSources.OVERRIDE, EntitlementSources.PLATFORM_ADMIN):
                if row.ends_at and row.ends_at < now:
                    continue
                result[row.feature_code] = bool(row.is_enabled)
            elif row.source == EntitlementSources.PLAN:
                result[row.feature_code] = bool(row.is_enabled)
        # Suspension / past_due hors grâce
        status = self._subscription_status(organization_id)
        if status in (SubscriptionStatus.SUSPENDED, SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED):
            for code in COSTLY_FEATURES_WHEN_SUSPENDED:
                if code in result:
                    result[code] = False
            for code in READ_FEATURES:
                result.setdefault(code, True)
        elif status == SubscriptionStatus.PAST_DUE and self._past_grace(organization_id, now):
            for code in COSTLY_FEATURES_WHEN_SUSPENDED:
                if code in result:
                    result[code] = False
        return result

    def rebuild_entitlements(
        self,
        organization_id: int,
        *,
        subscription_id: str | None = None,
        plan_code: str | None = None,
    ) -> dict[str, bool]:
        features = dict(get_plan(plan_code or self._plan_code(organization_id) or "starter").features) if get_plan(
            plan_code or self._plan_code(organization_id) or "starter"
        ) else {}
        if not features:
            from app.billing.plan_registry import STARTER_FEATURES

            features = dict(STARTER_FEATURES)

        self.repo.delete_entitlements_by_source(
            organization_id,
            [EntitlementSources.PLAN, EntitlementSources.TRIAL],
        )
        sub = self.repo.get_current_subscription(organization_id)
        sub_id = subscription_id or (sub.subscription_id if sub else None)
        source = EntitlementSources.TRIAL if (sub and sub.status == SubscriptionStatus.TRIALING) else EntitlementSources.PLAN
        now = datetime.utcnow()
        for code, enabled in features.items():
            self.db.add(
                ElfisEntitlement(
                    id=str(uuid4()),
                    entitlement_id=str(uuid4()),
                    organization_id=organization_id,
                    subscription_id=sub_id,
                    feature_code=code,
                    is_enabled=bool(enabled),
                    source=source,
                    created_at=now,
                    updated_at=now,
                )
            )
        self.db.flush()
        return self.get_entitlements(organization_id)

    def set_override(
        self,
        organization_id: int,
        feature_code: str,
        is_enabled: bool,
        *,
        source: str = EntitlementSources.PLATFORM_ADMIN,
        ends_at: datetime | None = None,
        value: dict | None = None,
        subscription_id: str | None = None,
    ) -> ElfisEntitlement:
        row = self.repo.get_entitlement(organization_id, feature_code, source)
        now = datetime.utcnow()
        if not row:
            row = ElfisEntitlement(
                id=str(uuid4()),
                entitlement_id=str(uuid4()),
                organization_id=organization_id,
                feature_code=feature_code,
                source=source,
            )
            self.db.add(row)
        row.is_enabled = bool(is_enabled)
        row.ends_at = ends_at
        row.value = value
        row.subscription_id = subscription_id
        row.updated_at = now
        if not row.created_at:
            row.created_at = now
        self.db.flush()
        return row

    def remove_override(
        self,
        organization_id: int,
        feature_code: str,
        *,
        source: str = EntitlementSources.PLATFORM_ADMIN,
    ) -> bool:
        row = self.repo.get_entitlement(organization_id, feature_code, source)
        if not row:
            return False
        self.db.delete(row)
        self.db.flush()
        return True

    def _resolve(self, organization_id: int, feature_code: str, *, now: datetime) -> bool:
        # 1. Suspension plateforme organisation
        from app.models_saas import Organization
        from app.platform_admin.admin_types import OrgPlatformStatus

        org = self.db.get(Organization, organization_id)
        if org is not None:
            status = getattr(org, "platform_status", None) or OrgPlatformStatus.ACTIVE
            if status == OrgPlatformStatus.SUSPENDED:
                return feature_code in READ_FEATURES

        # 1b. Suspension plateforme (legacy admin_revoked)
        from app.subscriptions.access import get_subscription_access

        access = get_subscription_access(self.db, organization_id)
        if access.admin_revoked:
            return feature_code in READ_FEATURES

        # 2. Overrides explicites
        for source in (EntitlementSources.PLATFORM_ADMIN, EntitlementSources.OVERRIDE):
            row = self.repo.get_entitlement(organization_id, feature_code, source)
            if row and (not row.ends_at or row.ends_at >= now):
                return bool(row.is_enabled)

        # 3. Statut abonnement
        if not access.has_access and not access.read_only:
            return False
        if access.read_only and feature_code in COSTLY_FEATURES_WHEN_SUSPENDED:
            return False

        # 4–5. Plan / trial features
        features = self.get_entitlements(organization_id, now=now)
        if feature_code in features:
            return bool(features[feature_code])

        # 6. Défaut sécurisé
        return False

    def _effective_plan_features(self, organization_id: int) -> dict[str, bool]:
        code = self._plan_code(organization_id) or "starter"
        plan = get_plan(code) or get_plan("starter")
        return dict(plan.features) if plan else {}

    def _plan_code(self, organization_id: int) -> str | None:
        sub = self.repo.get_current_subscription(organization_id)
        if sub:
            from app.billing.billing_models import ElfisBillingPlan

            plan = (
                self.db.query(ElfisBillingPlan)
                .filter(ElfisBillingPlan.plan_id == sub.plan_id)
                .first()
            )
            if plan:
                return plan.plan_code
            # plan_id peut être un plan_code stocké
            if get_plan(sub.plan_id):
                return sub.plan_id
        from app.billing.plan_registry import default_plan_code, plan_code_for_stripe_price
        from app.models_saas import Subscription as LegacySubscription

        legacy = (
            self.db.query(LegacySubscription)
            .filter(LegacySubscription.organization_id == organization_id)
            .order_by(LegacySubscription.id.desc())
            .first()
        )
        if legacy and legacy.stripe_price_id:
            mapped = plan_code_for_stripe_price(legacy.stripe_price_id)
            if mapped:
                return mapped
        return default_plan_code()

    def _subscription_status(self, organization_id: int) -> str:
        sub = self.repo.get_current_subscription(organization_id)
        if sub:
            return sub.status
        from app.models_saas import Subscription as LegacySubscription
        from app.billing.billing_types import STRIPE_STATUS_MAP

        legacy = (
            self.db.query(LegacySubscription)
            .filter(LegacySubscription.organization_id == organization_id)
            .order_by(LegacySubscription.id.desc())
            .first()
        )
        if not legacy:
            return SubscriptionStatus.EXPIRED
        return STRIPE_STATUS_MAP.get(legacy.status, legacy.status)

    def _past_grace(self, organization_id: int, now: datetime) -> bool:
        sub = self.repo.get_current_subscription(organization_id)
        if sub and sub.grace_period_ends_at:
            return now > sub.grace_period_ends_at
        from app.subscriptions.access import get_subscription_access

        access = get_subscription_access(self.db, organization_id, now=now)
        if access.grace_until:
            return now > access.grace_until
        return True
