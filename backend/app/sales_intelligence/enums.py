"""Sales Intelligence V1 — deterministic enums (no generative AI)."""

from __future__ import annotations

from enum import StrEnum


class InsightStatus(StrEnum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"
    dismissed = "dismissed"
    expired = "expired"


class InsightCategory(StrEnum):
    focus = "focus"
    opportunity = "opportunity"
    pipeline = "pipeline"
    activity = "activity"
    task = "task"
    relationship = "relationship"
    proposal = "proposal"
    conversion = "conversion"
    performance = "performance"


class InsightSeverity(StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


SEVERITY_RANK: dict[str, int] = {
    InsightSeverity.info.value: 10,
    InsightSeverity.low.value: 20,
    InsightSeverity.medium.value: 30,
    InsightSeverity.high.value: 40,
    InsightSeverity.critical.value: 50,
}


class InsightType(StrEnum):
    # Focus / tasks
    task_critical_overdue = "task_critical_overdue"
    meeting_imminent = "meeting_imminent"
    # Opportunities
    opportunity_inactive_high_value = "opportunity_inactive_high_value"
    opportunity_no_next_action = "opportunity_no_next_action"
    opportunity_stage_aging = "opportunity_stage_aging"
    opportunity_closing_overdue = "opportunity_closing_overdue"
    opportunity_closing_low_readiness = "opportunity_closing_low_readiness"
    opportunity_low_health_high_value = "opportunity_low_health_high_value"
    opportunity_no_proposal_near_close = "opportunity_no_proposal_near_close"
    # Pipeline aggregates
    pipeline_stage_congested = "pipeline_stage_congested"
    pipeline_high_risk_concentration = "pipeline_high_risk_concentration"
    pipeline_many_without_next_action = "pipeline_many_without_next_action"
    # Tasks / activities
    tasks_overdue_on_deal = "tasks_overdue_on_deal"
    no_activity_planned_today = "no_activity_planned_today"
    # Relationship
    relationship_fragile = "relationship_fragile"
    # Proposals
    proposal_approved_unsent = "proposal_approved_unsent"
    proposal_expiring_soon = "proposal_expiring_soon"
    proposal_expired_open_opportunity = "proposal_expired_open_opportunity"
    proposal_negotiation_long = "proposal_negotiation_long"
    proposal_accepted_unconverted = "proposal_accepted_unconverted"
    proposal_conversion_failed = "proposal_conversion_failed"
    proposal_conversion_ready = "proposal_conversion_ready"
    proposal_almost_ready = "proposal_almost_ready"


# Insights that may project to Decision Center (actionable)
ACTIONABLE_DECISION_TYPES: frozenset[str] = frozenset(
    {
        InsightType.task_critical_overdue.value,
        InsightType.opportunity_inactive_high_value.value,
        InsightType.opportunity_no_next_action.value,
        InsightType.proposal_accepted_unconverted.value,
        InsightType.proposal_conversion_failed.value,
        InsightType.proposal_expiring_soon.value,
    }
)

# Notify only these (critical / near deadline)
NOTIFIABLE_TYPES: frozenset[str] = frozenset(
    {
        InsightType.task_critical_overdue.value,
        InsightType.proposal_expiring_soon.value,
        InsightType.proposal_conversion_failed.value,
        InsightType.opportunity_inactive_high_value.value,
    }
)
