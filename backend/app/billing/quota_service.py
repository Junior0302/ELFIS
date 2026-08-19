"""QuotaService — limites et réservations atomiques."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.billing.billing_exceptions import QuotaExceededError
from app.billing.billing_models import ElfisQuota, ElfisUsageCounter
from app.billing.billing_repository import BillingRepository
from app.billing.billing_schemas import QuotaCheckResult
from app.billing.billing_types import QuotaPeriods
from app.billing.plan_registry import get_plan
from app.config import settings


def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime(now.year, now.month, 1)
    last = monthrange(now.year, now.month)[1]
    end = datetime(now.year, now.month, last, 23, 59, 59)
    return start, end


class QuotaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)

    def _enforce(self) -> bool:
        return bool(getattr(settings, "elfis_billing_enforce_quotas", False))

    def check(
        self,
        organization_id: int,
        quota_code: str,
        *,
        amount: int = 1,
        now: datetime | None = None,
    ) -> QuotaCheckResult:
        now = now or datetime.utcnow()
        quota = self._ensure_quota(organization_id, quota_code, now=now)
        usage = self._ensure_usage(organization_id, quota_code, quota, now=now)
        used = int(usage.used_value or 0) + int(usage.reserved_value or 0)
        limit = quota.limit_value
        if limit is None:
            remaining = None
            allowed = True
        else:
            remaining = max(0, int(limit) - used)
            allowed = used + amount <= int(limit)
            if not quota.hard_limit:
                allowed = True
        if not self._enforce() and limit is not None and not allowed:
            # Mode observation : toujours autoriser si enforce désactivé
            allowed = True
        return QuotaCheckResult(
            allowed=allowed,
            quota_code=quota_code,
            limit_value=int(limit) if limit is not None else None,
            used_value=used,
            remaining_value=remaining,
            period_started_at=quota.current_period_started_at,
            period_ends_at=quota.current_period_ends_at,
            hard_limit=bool(quota.hard_limit),
        )

    def consume(
        self,
        organization_id: int,
        quota_code: str,
        amount: int = 1,
        *,
        now: datetime | None = None,
    ) -> QuotaCheckResult:
        result = self.check(organization_id, quota_code, amount=amount, now=now)
        if not result.allowed:
            raise QuotaExceededError(quota_code)
        quota = self._ensure_quota(organization_id, quota_code, now=now or datetime.utcnow())
        usage = self._ensure_usage(organization_id, quota_code, quota, now=now or datetime.utcnow())
        # Incrément conditionnel : empêche le dépassement sous concurrence (enforce + hard_limit).
        where = [ElfisUsageCounter.id == usage.id]
        if (
            self._enforce()
            and quota.hard_limit
            and quota.limit_value is not None
        ):
            where.append(
                (ElfisUsageCounter.used_value + ElfisUsageCounter.reserved_value + amount)
                <= int(quota.limit_value)
            )
        upd = self.db.execute(
            update(ElfisUsageCounter)
            .where(*where)
            .values(
                used_value=ElfisUsageCounter.used_value + amount,
                last_consumed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        if upd.rowcount == 0:
            raise QuotaExceededError(quota_code)
        self.db.flush()
        return self.check(organization_id, quota_code, amount=0, now=now)

    def reserve(
        self,
        organization_id: int,
        quota_code: str,
        amount: int = 1,
        *,
        now: datetime | None = None,
    ) -> QuotaCheckResult:
        result = self.check(organization_id, quota_code, amount=amount, now=now)
        if not result.allowed:
            raise QuotaExceededError(quota_code)
        quota = self._ensure_quota(organization_id, quota_code, now=now or datetime.utcnow())
        usage = self._ensure_usage(organization_id, quota_code, quota, now=now or datetime.utcnow())
        where = [ElfisUsageCounter.id == usage.id]
        if (
            self._enforce()
            and quota.hard_limit
            and quota.limit_value is not None
        ):
            where.append(
                (ElfisUsageCounter.used_value + ElfisUsageCounter.reserved_value + amount)
                <= int(quota.limit_value)
            )
        upd = self.db.execute(
            update(ElfisUsageCounter)
            .where(*where)
            .values(
                reserved_value=ElfisUsageCounter.reserved_value + amount,
                updated_at=datetime.utcnow(),
            )
        )
        if upd.rowcount == 0:
            raise QuotaExceededError(quota_code)
        self.db.flush()
        return self.check(organization_id, quota_code, amount=0, now=now)

    def commit_reservation(
        self,
        organization_id: int,
        quota_code: str,
        amount: int = 1,
        *,
        now: datetime | None = None,
    ) -> None:
        quota = self._ensure_quota(organization_id, quota_code, now=now or datetime.utcnow())
        usage = self._ensure_usage(organization_id, quota_code, quota, now=now or datetime.utcnow())
        reserved = max(0, int(usage.reserved_value or 0) - amount)
        self.db.execute(
            update(ElfisUsageCounter)
            .where(ElfisUsageCounter.id == usage.id)
            .values(
                reserved_value=reserved,
                used_value=ElfisUsageCounter.used_value + amount,
                last_consumed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        self.db.flush()

    def release_reservation(
        self,
        organization_id: int,
        quota_code: str,
        amount: int = 1,
        *,
        now: datetime | None = None,
    ) -> None:
        quota = self._ensure_quota(organization_id, quota_code, now=now or datetime.utcnow())
        usage = self._ensure_usage(organization_id, quota_code, quota, now=now or datetime.utcnow())
        reserved = max(0, int(usage.reserved_value or 0) - amount)
        self.db.execute(
            update(ElfisUsageCounter)
            .where(ElfisUsageCounter.id == usage.id)
            .values(reserved_value=reserved, updated_at=datetime.utcnow())
        )
        self.db.flush()

    def get_usage(self, organization_id: int, quota_code: str) -> QuotaCheckResult:
        return self.check(organization_id, quota_code, amount=0)

    def reset_period(self, organization_id: int, quota_code: str, *, now: datetime | None = None) -> ElfisQuota:
        now = now or datetime.utcnow()
        start, end = _month_bounds(now)
        existing = (
            self.db.query(ElfisQuota)
            .filter(
                ElfisQuota.organization_id == organization_id,
                ElfisQuota.quota_code == quota_code,
            )
            .order_by(ElfisQuota.current_period_started_at.desc())
            .first()
        )
        limit = existing.limit_value if existing else None
        hard = existing.hard_limit if existing else True
        row = ElfisQuota(
            id=str(uuid4()),
            quota_id=str(uuid4()),
            organization_id=organization_id,
            subscription_id=existing.subscription_id if existing else None,
            quota_code=quota_code,
            limit_value=limit,
            period=QuotaPeriods.MONTH,
            hard_limit=hard,
            current_period_started_at=start,
            current_period_ends_at=end,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def rebuild_quotas(
        self,
        organization_id: int,
        *,
        plan_code: str | None = None,
        subscription_id: str | None = None,
        now: datetime | None = None,
    ) -> list[ElfisQuota]:
        now = now or datetime.utcnow()
        from app.billing.plan_registry import default_plan_code

        code = plan_code or default_plan_code()
        plan = get_plan(code)
        quotas_def = dict(plan.quotas) if plan else {}
        start, end = _month_bounds(now)
        sub = self.repo.get_current_subscription(organization_id)
        sub_id = subscription_id or (sub.subscription_id if sub else None)
        if sub and sub.current_period_started_at and sub.current_period_ends_at:
            start = sub.current_period_started_at
            end = sub.current_period_ends_at
        rows: list[ElfisQuota] = []
        for qcode, limit in quotas_def.items():
            existing = self.repo.get_quota(organization_id, qcode, start)
            if existing:
                existing.limit_value = limit
                existing.subscription_id = sub_id
                existing.current_period_ends_at = end
                existing.updated_at = now
                rows.append(existing)
            else:
                row = ElfisQuota(
                    id=str(uuid4()),
                    quota_id=str(uuid4()),
                    organization_id=organization_id,
                    subscription_id=sub_id,
                    quota_code=qcode,
                    limit_value=limit,
                    period=QuotaPeriods.MONTH if ".month" in qcode else QuotaPeriods.LIFETIME,
                    hard_limit=limit is not None,
                    current_period_started_at=start,
                    current_period_ends_at=end if limit is not None else start + timedelta(days=36500),
                )
                self.db.add(row)
                rows.append(row)
        self.db.flush()
        return rows

    def _ensure_quota(self, organization_id: int, quota_code: str, *, now: datetime) -> ElfisQuota:
        start, end = _month_bounds(now)
        sub = self.repo.get_current_subscription(organization_id)
        if sub and sub.current_period_started_at:
            start = sub.current_period_started_at
            end = sub.current_period_ends_at or end
        row = self.repo.get_quota(organization_id, quota_code, start)
        if row:
            return row
        self.rebuild_quotas(organization_id, now=now)
        row = self.repo.get_quota(organization_id, quota_code, start)
        if row:
            return row
        # Quota inconnu = illimité
        row = ElfisQuota(
            id=str(uuid4()),
            quota_id=str(uuid4()),
            organization_id=organization_id,
            quota_code=quota_code,
            limit_value=None,
            period=QuotaPeriods.MONTH,
            hard_limit=False,
            current_period_started_at=start,
            current_period_ends_at=end,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _ensure_usage(
        self,
        organization_id: int,
        usage_code: str,
        quota: ElfisQuota,
        *,
        now: datetime,
    ) -> ElfisUsageCounter:
        # Map quota_code → usage_code (documents.processed.month → documents.processed)
        code = usage_code
        if code.endswith(".month"):
            code = code[: -len(".month")]
        row = self.repo.get_usage_counter(organization_id, code, quota.current_period_started_at)
        if row:
            return row
        row = ElfisUsageCounter(
            id=str(uuid4()),
            usage_counter_id=str(uuid4()),
            organization_id=organization_id,
            subscription_id=quota.subscription_id,
            usage_code=code,
            period_started_at=quota.current_period_started_at,
            period_ends_at=quota.current_period_ends_at,
            used_value=0,
            reserved_value=0,
        )
        self.db.add(row)
        self.db.flush()
        return row
