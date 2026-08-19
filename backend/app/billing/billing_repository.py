"""Repository Billing."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.billing.billing_models import (
    ElfisBillingEvent,
    ElfisBillingPlan,
    ElfisEntitlement,
    ElfisQuota,
    ElfisSubscription,
    ElfisUsageCounter,
)
from app.billing.billing_types import BillingEventStatus


class BillingRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Plans ---
    def get_plan_by_code(self, plan_code: str) -> ElfisBillingPlan | None:
        return (
            self.db.query(ElfisBillingPlan)
            .filter(ElfisBillingPlan.plan_code == plan_code)
            .first()
        )

    def upsert_plan_row(self, **kwargs) -> ElfisBillingPlan:
        code = kwargs["plan_code"]
        row = self.get_plan_by_code(code)
        if not row:
            row = ElfisBillingPlan(
                id=str(uuid4()),
                plan_id=str(uuid4()),
                plan_code=code,
            )
            self.db.add(row)
        for key, value in kwargs.items():
            if key == "plan_code":
                continue
            if hasattr(row, key):
                setattr(row, key, value)
        row.updated_at = datetime.utcnow()
        return row

    # --- Subscriptions ---
    def get_current_subscription(self, organization_id: int) -> ElfisSubscription | None:
        return (
            self.db.query(ElfisSubscription)
            .filter(
                ElfisSubscription.organization_id == organization_id,
                ElfisSubscription.is_current.is_(True),
            )
            .first()
        )

    def get_subscription_by_id(self, subscription_id: str) -> ElfisSubscription | None:
        return (
            self.db.query(ElfisSubscription)
            .filter(ElfisSubscription.subscription_id == subscription_id)
            .first()
        )

    def list_subscriptions(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ElfisSubscription]:
        q = self.db.query(ElfisSubscription).filter(ElfisSubscription.is_current.is_(True))
        if status:
            q = q.filter(ElfisSubscription.status == status)
        return q.order_by(ElfisSubscription.updated_at.desc()).offset(offset).limit(limit).all()

    def mark_others_not_current(self, organization_id: int, keep_id: str | None = None) -> None:
        q = self.db.query(ElfisSubscription).filter(
            ElfisSubscription.organization_id == organization_id,
            ElfisSubscription.is_current.is_(True),
        )
        if keep_id:
            q = q.filter(ElfisSubscription.subscription_id != keep_id)
        for row in q.all():
            row.is_current = False
            row.updated_at = datetime.utcnow()

    # --- Entitlements ---
    def list_entitlements(self, organization_id: int) -> list[ElfisEntitlement]:
        return (
            self.db.query(ElfisEntitlement)
            .filter(ElfisEntitlement.organization_id == organization_id)
            .all()
        )

    def get_entitlement(
        self, organization_id: int, feature_code: str, source: str
    ) -> ElfisEntitlement | None:
        return (
            self.db.query(ElfisEntitlement)
            .filter(
                ElfisEntitlement.organization_id == organization_id,
                ElfisEntitlement.feature_code == feature_code,
                ElfisEntitlement.source == source,
            )
            .first()
        )

    def delete_entitlements_by_source(self, organization_id: int, sources: list[str]) -> None:
        (
            self.db.query(ElfisEntitlement)
            .filter(
                ElfisEntitlement.organization_id == organization_id,
                ElfisEntitlement.source.in_(sources),
            )
            .delete(synchronize_session=False)
        )

    # --- Quotas ---
    def get_quota(
        self, organization_id: int, quota_code: str, period_started_at: datetime
    ) -> ElfisQuota | None:
        return (
            self.db.query(ElfisQuota)
            .filter(
                ElfisQuota.organization_id == organization_id,
                ElfisQuota.quota_code == quota_code,
                ElfisQuota.current_period_started_at == period_started_at,
            )
            .first()
        )

    def list_quotas(self, organization_id: int) -> list[ElfisQuota]:
        return (
            self.db.query(ElfisQuota)
            .filter(ElfisQuota.organization_id == organization_id)
            .order_by(ElfisQuota.quota_code.asc())
            .all()
        )

    # --- Usage ---
    def get_usage_counter(
        self, organization_id: int, usage_code: str, period_started_at: datetime
    ) -> ElfisUsageCounter | None:
        return (
            self.db.query(ElfisUsageCounter)
            .filter(
                ElfisUsageCounter.organization_id == organization_id,
                ElfisUsageCounter.usage_code == usage_code,
                ElfisUsageCounter.period_started_at == period_started_at,
            )
            .first()
        )

    def list_usage(self, organization_id: int) -> list[ElfisUsageCounter]:
        return (
            self.db.query(ElfisUsageCounter)
            .filter(ElfisUsageCounter.organization_id == organization_id)
            .order_by(ElfisUsageCounter.usage_code.asc())
            .all()
        )

    # --- Events ---
    def get_event_by_provider_id(self, provider_event_id: str) -> ElfisBillingEvent | None:
        return (
            self.db.query(ElfisBillingEvent)
            .filter(ElfisBillingEvent.provider_event_id == provider_event_id)
            .first()
        )

    def create_event(
        self,
        *,
        provider: str,
        provider_event_id: str | None,
        event_type: str,
        organization_id: int | None = None,
        subscription_id: str | None = None,
        payload_hash: str | None = None,
        payload_summary: dict | None = None,
    ) -> ElfisBillingEvent:
        row = ElfisBillingEvent(
            id=str(uuid4()),
            billing_event_id=str(uuid4()),
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            status=BillingEventStatus.RECEIVED,
            organization_id=organization_id,
            subscription_id=subscription_id,
            payload_hash=payload_hash,
            payload_summary=payload_summary or {},
            attempt_count=0,
            received_at=datetime.utcnow(),
        )
        self.db.add(row)
        return row

    def mark_event_processed(self, row: ElfisBillingEvent) -> None:
        row.status = BillingEventStatus.PROCESSED
        row.processed_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()

    def mark_event_failed(self, row: ElfisBillingEvent, error: str) -> None:
        row.status = BillingEventStatus.FAILED
        row.failed_at = datetime.utcnow()
        row.last_error = (error or "")[:2000]
        row.attempt_count = int(row.attempt_count or 0) + 1
        row.updated_at = datetime.utcnow()
