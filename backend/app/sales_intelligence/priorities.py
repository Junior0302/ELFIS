"""Thresholds and priority scoring — documented, deterministic."""

from __future__ import annotations

from decimal import Decimal

from app.sales_intelligence.enums import SEVERITY_RANK, InsightSeverity

# Absolute thresholds (documented method — no fictional quotas)
HIGH_VALUE_AMOUNT = Decimal("10000")
INACTIVE_DAYS = 7
STAGE_AGING_DAYS = 14
STAGE_AGING_CRITICAL_DAYS = 30
CLOSING_SOON_DAYS = 7
PROPOSAL_EXPIRING_DAYS = 3
MEETING_IMMINENT_HOURS = 4
NEGOTIATION_LONG_DAYS = 14
CONGESTED_STAGE_COUNT = 8
MANY_WITHOUT_NEXT_ACTION = 5
HIGH_RISK_SHARE = 0.35  # 35% of open opps at high/critical risk
FRAGILE_RELATIONSHIP = 40
LOW_HEALTH = 40
LOW_READINESS = 70


def priority_score(
    *,
    severity: str,
    amount: Decimal | float | int | None = None,
    days_until_deadline: int | None = None,
    days_inactive: int | None = None,
    impact_boost: int = 0,
) -> int:
    """Internal 0–100 priority. Not shown raw without explanation."""
    base = SEVERITY_RANK.get(severity, 20)
    score = min(50, base)
    if amount is not None:
        amt = Decimal(str(amount))
        if amt >= HIGH_VALUE_AMOUNT * 5:
            score += 25
        elif amt >= HIGH_VALUE_AMOUNT * 2:
            score += 18
        elif amt >= HIGH_VALUE_AMOUNT:
            score += 12
        elif amt >= Decimal("2000"):
            score += 6
    if days_until_deadline is not None:
        if days_until_deadline <= 0:
            score += 20
        elif days_until_deadline <= 2:
            score += 15
        elif days_until_deadline <= 7:
            score += 8
    if days_inactive is not None:
        if days_inactive >= 21:
            score += 12
        elif days_inactive >= INACTIVE_DAYS:
            score += 8
    score += max(0, min(15, impact_boost))
    return max(0, min(100, score))


def severity_for_inactive_high_value(*, days_inactive: int, amount: Decimal) -> str:
    if amount >= HIGH_VALUE_AMOUNT * 3 and days_inactive >= 14:
        return InsightSeverity.critical.value
    if amount >= HIGH_VALUE_AMOUNT and days_inactive >= INACTIVE_DAYS:
        return InsightSeverity.high.value
    return InsightSeverity.medium.value
