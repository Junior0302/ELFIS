"""SalesIntelligenceService — sync, focus, overview, acknowledge/dismiss."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.decision_center.enums import (
    DecisionActionType,
    DecisionSeverity,
    DecisionSourceType,
    DecisionType,
)
from app.decision_center.rules import DecisionDraft
from app.decision_center.service import DecisionCenterService
from app.events.event_types import EventNames
from app.notifications.notification_schemas import NotificationRequest
from app.notifications.notification_service import NotificationService
from app.sales_intelligence.enums import (
    InsightCategory,
    InsightSeverity,
    InsightStatus,
    InsightType,
    SEVERITY_RANK,
)
from app.sales_intelligence.events import publish_insight_event
from app.sales_intelligence.models import SalesInsightItem
from app.sales_intelligence.repository import InsightRepository
from app.sales_intelligence.rules import InsightRulesEngine
from app.sales_intelligence.schemas import (
    IntelligenceOverviewOut,
    IntelligenceSummaryOut,
    SalesFocusOut,
    SyncOut,
)


def _now() -> datetime:
    return datetime.utcnow()


# Focus resolution order (explicit)
FOCUS_TYPE_ORDER: tuple[str, ...] = (
    InsightType.task_critical_overdue.value,
    InsightType.meeting_imminent.value,
    InsightType.opportunity_inactive_high_value.value,
    InsightType.proposal_expiring_soon.value,
    InsightType.proposal_accepted_unconverted.value,
    InsightType.proposal_conversion_failed.value,
    InsightType.opportunity_no_next_action.value,
    InsightType.pipeline_stage_congested.value,
)


class SalesIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InsightRepository(db)
        self.rules = InsightRulesEngine(db)

    def sync(self, *, organization_id: int, user_id: int | None = None) -> SyncOut:
        drafts = self.rules.collect(organization_id)
        seen_keys: set[str] = set()
        created = updated = resolved = decisions = notifications = 0
        scanned_opps = min(len([d for d in drafts if d.source_type == "sales_opportunity"]), 120)
        scanned_props = min(len([d for d in drafts if d.source_type == "sales_proposal"]), 80)
        scanned_tasks = min(len([d for d in drafts if d.source_type == "sales_task"]), 80)

        for draft in drafts:
            seen_keys.add(draft.deduplication_key)
            row, event = self.repo.upsert_from_draft(organization_id, draft)
            if event == "created":
                created += 1
                publish_insight_event(
                    self.db,
                    event_name=EventNames.SALES_INSIGHT_CREATED,
                    organization_id=organization_id,
                    insight=row,
                    actor_user_id=user_id,
                    idempotency_key=f"sales:insight:created:{row.deduplication_key}",
                )
            elif event in ("updated", "reopened"):
                updated += 1
                publish_insight_event(
                    self.db,
                    event_name=EventNames.SALES_INSIGHT_UPDATED,
                    organization_id=organization_id,
                    insight=row,
                    actor_user_id=user_id,
                    idempotency_key=f"sales:insight:updated:{row.id}:{row.last_detected_at.isoformat()}",
                )

            if draft.project_decision and row.status in (
                InsightStatus.active.value,
                InsightStatus.acknowledged.value,
            ):
                if self._project_decision(organization_id, row, user_id):
                    decisions += 1

            if draft.notify and row.status == InsightStatus.active.value:
                if self._maybe_notify(organization_id, row, user_id):
                    notifications += 1

        # Resolve stale active insights not redetected (except dismissed)
        active_rows = (
            self.db.query(SalesInsightItem)
            .filter(
                SalesInsightItem.organization_id == organization_id,
                SalesInsightItem.status.in_(
                    (InsightStatus.active.value, InsightStatus.acknowledged.value)
                ),
            )
            .all()
        )
        for row in active_rows:
            if row.deduplication_key not in seen_keys:
                row.status = InsightStatus.resolved.value
                row.resolved_at = _now()
                row.updated_at = _now()
                resolved += 1
                publish_insight_event(
                    self.db,
                    event_name=EventNames.SALES_INSIGHT_RESOLVED,
                    organization_id=organization_id,
                    insight=row,
                    actor_user_id=user_id,
                    idempotency_key=f"sales:insight:resolved:{row.id}:{row.resolved_at.isoformat()}",
                )
                if row.linked_decision_id:
                    DecisionCenterService(self.db).resolve_by_source(
                        organization_id=organization_id,
                        source_type=DecisionSourceType.SALES_INSIGHT,
                        source_id=str(row.id),
                        commit=False,
                    )

        self.db.flush()
        return SyncOut(
            created=created,
            updated=updated,
            resolved=resolved,
            decisions_created=decisions,
            notifications_created=notifications,
            scanned_opportunities=scanned_opps,
            scanned_proposals=scanned_props,
            scanned_tasks=scanned_tasks,
        )

    def _project_decision(
        self, organization_id: int, row: SalesInsightItem, user_id: int | None
    ) -> bool:
        if row.linked_decision_id:
            return False
        # Map severity
        sev = row.severity
        if sev not in (
            DecisionSeverity.HIGH.value,
            DecisionSeverity.CRITICAL.value,
            DecisionSeverity.MEDIUM.value,
        ):
            return False
        draft = DecisionDraft(
            decision_type=DecisionType.SALES_INSIGHT_REQUIRES_ACTION,
            source_type=DecisionSourceType.SALES_INSIGHT,
            source_id=str(row.id),
            severity=sev if sev in {s.value for s in DecisionSeverity} else DecisionSeverity.HIGH.value,
            title=row.title,
            summary=row.summary,
            explanation=(row.explanation or {}).get("why_it_matters") or row.summary,
            recommended_action_type=DecisionActionType.OPEN_RESOURCE,
            recommended_action_path=row.route,
            required_permission="sales.intelligence.read",
            created_by_rule=f"sales_insight:{row.insight_type}",
            rule_version="1",
            deduplication_key=f"sales_insight_requires_action:{row.id}:v1",
            metadata={"insight_type": row.insight_type, "category": row.category},
            still_active=True,
        )
        decision = DecisionCenterService(self.db).apply_draft(
            organization_id=organization_id, draft=draft, commit=False
        )
        row.linked_decision_id = decision.id
        return True

    def _maybe_notify(
        self, organization_id: int, row: SalesInsightItem, user_id: int | None
    ) -> bool:
        if row.severity not in (InsightSeverity.critical.value, InsightSeverity.high.value):
            return False
        try:
            result = NotificationService(self.db).create_notification(
                NotificationRequest(
                    organization_id=organization_id,
                    user_id=user_id,
                    notification_type="sales_insight",
                    category="sales",
                    severity=row.severity,
                    template_name="system_generic",
                    template_data={
                        "title": row.title,
                        "message": row.summary[:200],
                        "severity": row.severity,
                    },
                    channels=["in_app"],
                    action_url=row.route or f"/sales/intelligence/{row.id}",
                    action_label="Voir",
                    related_entity_type="sales_insight",
                    related_entity_id=str(row.id),
                    idempotency_key=f"sales:insight:notify:{row.deduplication_key}:{row.severity}",
                )
            )
            created = getattr(result, "created", None)
            if created is None:
                created = not getattr(result, "deduplicated", False)
            return bool(created)
        except Exception:
            # Template may be missing — do not fail sync
            return False

    def resolve_sales_focus(self, *, organization_id: int) -> SalesFocusOut:
        rows = self.repo.active_for_org(organization_id, limit=80)
        by_type: dict[str, list[SalesInsightItem]] = {}
        for r in rows:
            by_type.setdefault(r.insight_type, []).append(r)

        chosen: SalesInsightItem | None = None
        for itype in FOCUS_TYPE_ORDER:
            candidates = by_type.get(itype) or []
            if candidates:
                chosen = max(candidates, key=lambda x: (x.priority_score, SEVERITY_RANK.get(x.severity, 0)))
                break

        if chosen is None and rows:
            # Fallback: highest priority non-info
            actionable = [r for r in rows if r.severity not in (InsightSeverity.info.value,)]
            if actionable:
                chosen = actionable[0]

        now = _now()
        if chosen is None:
            return SalesFocusOut(
                title="Aucune urgence commerciale actuellement",
                summary="Aucune priorité critique détectée. Vous pouvez examiner le pipeline ou créer une opportunité.",
                reason="Aucune règle de focus n’a trouvé de signal urgent.",
                severity=InsightSeverity.info.value,
                tone="no_urgent_focus",
                route="/sales/pipeline",
                action_label="Examiner le pipeline",
                source_type=None,
                source_id=None,
                evidence=[],
                insight_id=None,
                generated_at=now,
            )

        tone = "normal"
        if chosen.severity == InsightSeverity.critical.value:
            tone = "urgent"
        elif chosen.severity == InsightSeverity.high.value:
            tone = "important"

        return SalesFocusOut(
            title=chosen.title,
            summary=chosen.summary,
            reason=(chosen.explanation or {}).get("rule_applied")
            or (chosen.explanation or {}).get("why_it_matters")
            or chosen.summary,
            severity=chosen.severity,
            tone=tone,
            route=chosen.route,
            action_label=(chosen.recommended_action or {}).get("label") or "Ouvrir",
            source_type=chosen.source_type,
            source_id=chosen.source_id,
            evidence=chosen.evidence or [],
            insight_id=chosen.id,
            generated_at=now,
        )

    def build_overview(self, *, organization_id: int, auto_sync: bool = True) -> IntelligenceOverviewOut:
        if auto_sync:
            self.sync(organization_id=organization_id)
        focus = self.resolve_sales_focus(organization_id=organization_id)
        rows = self.repo.active_for_org(organization_id, limit=100)
        summary = self._counts(organization_id)

        def take(cat: str, n: int = 5) -> list:
            from app.sales_intelligence.schemas import InsightOut

            return [InsightOut.model_validate(r) for r in rows if r.category == cat][:n]

        from app.sales_intelligence.schemas import InsightOut

        return IntelligenceOverviewOut(
            focus=focus,
            summary=summary,
            top_insights=[InsightOut.model_validate(r) for r in rows[:3]],
            opportunity_insights=take(InsightCategory.opportunity.value),
            pipeline_insights=take(InsightCategory.pipeline.value),
            proposal_insights=take(InsightCategory.proposal.value)
            + take(InsightCategory.conversion.value),
            activity_insights=take(InsightCategory.activity.value)
            + take(InsightCategory.task.value),
            counts=summary,
            generated_at=_now(),
            stale=False,
        )

    def _counts(self, organization_id: int) -> IntelligenceSummaryOut:
        rows = self.repo.active_for_org(organization_id, limit=500)
        return IntelligenceSummaryOut(
            active_count=len([r for r in rows if r.status == InsightStatus.active.value]),
            critical_count=len([r for r in rows if r.severity == InsightSeverity.critical.value]),
            high_count=len([r for r in rows if r.severity == InsightSeverity.high.value]),
            opportunity_count=len([r for r in rows if r.category == InsightCategory.opportunity.value]),
            pipeline_count=len([r for r in rows if r.category == InsightCategory.pipeline.value]),
            proposal_count=len(
                [
                    r
                    for r in rows
                    if r.category
                    in (InsightCategory.proposal.value, InsightCategory.conversion.value)
                ]
            ),
            task_count=len(
                [
                    r
                    for r in rows
                    if r.category in (InsightCategory.task.value, InsightCategory.activity.value)
                ]
            ),
            acknowledged_count=len(
                [r for r in rows if r.status == InsightStatus.acknowledged.value]
            ),
        )

    def get_insight(self, *, organization_id: int, insight_id: int) -> SalesInsightItem:
        row = self.repo.get(organization_id, insight_id)
        if not row:
            raise HTTPException(
                404, detail={"code": "not_found", "message": "Insight introuvable"}
            )
        return row

    def acknowledge(
        self, *, organization_id: int, insight_id: int, user_id: int | None
    ) -> SalesInsightItem:
        row = self.get_insight(organization_id=organization_id, insight_id=insight_id)
        if row.status not in (InsightStatus.active.value, InsightStatus.acknowledged.value):
            raise HTTPException(
                409,
                detail={"code": "invalid_status", "message": "Insight non actif"},
            )
        row.status = InsightStatus.acknowledged.value
        row.acknowledged_at = _now()
        row.acknowledged_by = user_id
        row.updated_at = _now()
        publish_insight_event(
            self.db,
            event_name=EventNames.SALES_INSIGHT_ACKNOWLEDGED,
            organization_id=organization_id,
            insight=row,
            actor_user_id=user_id,
        )
        self.db.flush()
        return row

    def dismiss(
        self,
        *,
        organization_id: int,
        insight_id: int,
        user_id: int | None,
        reason: str | None = None,
    ) -> SalesInsightItem:
        row = self.get_insight(organization_id=organization_id, insight_id=insight_id)
        if row.severity == InsightSeverity.critical.value and not (reason or "").strip():
            raise HTTPException(
                400,
                detail={
                    "code": "reason_required",
                    "message": "Un motif est requis pour écarter un insight critique",
                },
            )
        row.status = InsightStatus.dismissed.value
        row.dismissed_at = _now()
        row.dismissed_by = user_id
        row.dismiss_reason = (reason or "").strip() or None
        row.updated_at = _now()
        publish_insight_event(
            self.db,
            event_name=EventNames.SALES_INSIGHT_DISMISSED,
            organization_id=organization_id,
            insight=row,
            actor_user_id=user_id,
        )
        self.db.flush()
        return row
