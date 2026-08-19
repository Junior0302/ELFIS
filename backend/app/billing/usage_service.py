"""UsageService — agrégation consommation (AI, documents, e-mails…)."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.billing.billing_models import ElfisUsageCounter
from app.billing.billing_repository import BillingRepository
from app.billing.billing_types import UsageCodes


def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = datetime(now.year, now.month, 1)
    last = monthrange(now.year, now.month)[1]
    end = datetime(now.year, now.month, last, 23, 59, 59)
    return start, end


class UsageService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)

    def record_usage(
        self,
        organization_id: int,
        usage_code: str,
        amount: int = 1,
        *,
        subscription_id: str | None = None,
        now: datetime | None = None,
    ) -> ElfisUsageCounter:
        now = now or datetime.utcnow()
        start, end = _month_bounds(now)
        sub = self.repo.get_current_subscription(organization_id)
        if sub and sub.current_period_started_at:
            start = sub.current_period_started_at
            end = sub.current_period_ends_at or end
            subscription_id = subscription_id or sub.subscription_id
        row = self.repo.get_usage_counter(organization_id, usage_code, start)
        if not row:
            row = ElfisUsageCounter(
                id=str(uuid4()),
                usage_counter_id=str(uuid4()),
                organization_id=organization_id,
                subscription_id=subscription_id,
                usage_code=usage_code,
                period_started_at=start,
                period_ends_at=end,
                used_value=0,
                reserved_value=0,
            )
            self.db.add(row)
            self.db.flush()
        self.db.execute(
            update(ElfisUsageCounter)
            .where(ElfisUsageCounter.id == row.id)
            .values(
                used_value=ElfisUsageCounter.used_value + int(amount),
                last_consumed_at=now,
                updated_at=now,
            )
        )
        self.db.flush()
        self.db.refresh(row)
        return row

    def get_current_usage(
        self, organization_id: int, usage_code: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
        now = now or datetime.utcnow()
        start, end = _month_bounds(now)
        sub = self.repo.get_current_subscription(organization_id)
        if sub and sub.current_period_started_at:
            start = sub.current_period_started_at
            end = sub.current_period_ends_at or end
        row = self.repo.get_usage_counter(organization_id, usage_code, start)
        return {
            "usage_code": usage_code,
            "used_value": int(row.used_value) if row else 0,
            "reserved_value": int(row.reserved_value) if row else 0,
            "period_started_at": start.isoformat() + "Z",
            "period_ends_at": end.isoformat() + "Z",
        }

    def list_usage(self, organization_id: int) -> list[dict[str, Any]]:
        return [
            {
                "usage_code": r.usage_code,
                "used_value": int(r.used_value or 0),
                "reserved_value": int(r.reserved_value or 0),
                "period_started_at": r.period_started_at.isoformat() + "Z" if r.period_started_at else None,
                "period_ends_at": r.period_ends_at.isoformat() + "Z" if r.period_ends_at else None,
                "last_consumed_at": r.last_consumed_at.isoformat() + "Z" if r.last_consumed_at else None,
            }
            for r in self.repo.list_usage(organization_id)
        ]

    def aggregate_usage(self, organization_id: int, *, now: datetime | None = None) -> dict[str, Any]:
        """Agrège compteurs locaux + elfis_ai_usage (tokens)."""
        now = now or datetime.utcnow()
        start, end = _month_bounds(now)
        local = {item["usage_code"]: item for item in self.list_usage(organization_id)}
        ai_tokens = self._aggregate_ai_tokens(organization_id, start, end)
        if ai_tokens is not None:
            local[UsageCodes.AI_TOKENS] = {
                "usage_code": UsageCodes.AI_TOKENS,
                "used_value": ai_tokens,
                "reserved_value": 0,
                "period_started_at": start.isoformat() + "Z",
                "period_ends_at": end.isoformat() + "Z",
                "source": "elfis_ai_usage",
            }
        return local

    def reconcile_usage(self, organization_id: int, *, now: datetime | None = None) -> dict[str, Any]:
        """Recale le compteur ai.tokens depuis elfis_ai_usage."""
        now = now or datetime.utcnow()
        start, end = _month_bounds(now)
        tokens = self._aggregate_ai_tokens(organization_id, start, end) or 0
        row = self.repo.get_usage_counter(organization_id, UsageCodes.AI_TOKENS, start)
        if not row:
            row = self.record_usage(organization_id, UsageCodes.AI_TOKENS, 0, now=now)
        row.used_value = tokens
        row.updated_at = now
        self.db.flush()
        return self.get_current_usage(organization_id, UsageCodes.AI_TOKENS, now=now)

    def _aggregate_ai_tokens(
        self, organization_id: int, start: datetime, end: datetime
    ) -> int | None:
        try:
            from app.ai.ai_models import ElfisAiUsage

            total = (
                self.db.query(func.coalesce(func.sum(ElfisAiUsage.total_tokens), 0))
                .filter(
                    ElfisAiUsage.organization_id == organization_id,
                    ElfisAiUsage.created_at >= start,
                    ElfisAiUsage.created_at <= end,
                )
                .scalar()
            )
            return int(total or 0)
        except Exception:
            return None
