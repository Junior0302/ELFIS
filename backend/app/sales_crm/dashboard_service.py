"""SalesDashboardService — single source of truth for SalesPilot dashboard KPIs.

All aggregation is server-side. Frontend must not recalculate metrics.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.sales_crm.dashboard_schemas import (
    SalesDashboardActivitiesOut,
    SalesDashboardActivityOut,
    SalesDashboardOpportunityOut,
    SalesDashboardOut,
    SalesDashboardSummaryOut,
    SalesDashboardTaskOut,
    SalesDashboardTasksOut,
    SalesPipelineOverviewOut,
    SalesPipelineStageOverviewOut,
    SalesQuickActionOut,
)
from app.sales_crm.models import (
    SalesActivity,
    SalesCompany,
    SalesLead,
    SalesOpportunity,
    SalesPipeline,
    SalesPipelineStage,
    SalesTask,
)
from app.sales_crm.service import ensure_default_pipeline, soft_alive

OPEN_LEAD_STATUSES = ("new", "contacted", "qualified")
OPEN_OPP_STATUS = "open"
WON_OPP_STATUS = "won"
LOST_OPP_STATUS = "lost"
ACTIVE_TASK_STATUSES = ("todo", "in_progress")
ACTIVITY_TYPES = ("call", "email", "meeting", "visit")

MAX_ACTIVITIES_PER_BUCKET = 8
MAX_TASKS_PER_BUCKET = 8
MAX_RECENT_OPPORTUNITIES = 8

QUICK_ACTIONS: tuple[SalesQuickActionOut, ...] = (
    SalesQuickActionOut(
        id="new_lead",
        label="Nouveau prospect",
        description="Créer un lead commercial",
        href="/sales/leads",
    ),
    SalesQuickActionOut(
        id="new_opportunity",
        label="Nouvelle opportunité",
        description="Ajouter une affaire au pipeline",
        href="/sales/pipeline",
    ),
    SalesQuickActionOut(
        id="new_activity",
        label="Nouvelle activité",
        description="Enregistrer un appel, email ou réunion",
        href="/sales/activities",
    ),
    SalesQuickActionOut(
        id="new_task",
        label="Nouvelle tâche",
        description="Planifier une action commerciale",
        href="/sales/tasks",
    ),
)


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min)
    end = datetime.combine(d, time.max)
    return start, end


class SalesDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def build(self, *, organization_id: int, user_id: int | None = None) -> SalesDashboardOut:
        pipeline_row = ensure_default_pipeline(
            self.db, organization_id=organization_id, user_id=user_id
        )
        self.db.flush()

        summary = self._summary(organization_id)
        pipeline = self._pipeline_overview(organization_id, pipeline_row)
        activities = self._activities(organization_id)
        tasks = self._tasks(organization_id)
        recent = self._recent_opportunities(organization_id)

        return SalesDashboardOut(
            summary=summary,
            pipeline=pipeline,
            activities=activities,
            tasks=tasks,
            recent_opportunities=recent,
            quick_actions=list(QUICK_ACTIONS),
            generated_at=datetime.utcnow(),
        )

    def _summary(self, organization_id: int) -> SalesDashboardSummaryOut:
        today = date.today()
        today_start, today_end = _day_bounds(today)
        now = datetime.utcnow()

        open_leads = (
            soft_alive(self.db.query(func.count(SalesLead.id)), SalesLead)
            .filter(
                SalesLead.organization_id == organization_id,
                SalesLead.status.in_(OPEN_LEAD_STATUSES),
            )
            .scalar()
            or 0
        )

        open_opps = (
            soft_alive(self.db.query(func.count(SalesOpportunity.id)), SalesOpportunity)
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == OPEN_OPP_STATUS,
            )
            .scalar()
            or 0
        )

        won = (
            soft_alive(self.db.query(func.count(SalesOpportunity.id)), SalesOpportunity)
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == WON_OPP_STATUS,
            )
            .scalar()
            or 0
        )

        lost = (
            soft_alive(self.db.query(func.count(SalesOpportunity.id)), SalesOpportunity)
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == LOST_OPP_STATUS,
            )
            .scalar()
            or 0
        )

        pipeline_value = (
            soft_alive(
                self.db.query(func.coalesce(func.sum(SalesOpportunity.estimated_amount), 0)),
                SalesOpportunity,
            )
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == OPEN_OPP_STATUS,
            )
            .scalar()
            or 0
        )

        weighted = (
            soft_alive(
                self.db.query(
                    func.coalesce(
                        func.sum(
                            SalesOpportunity.estimated_amount
                            * SalesOpportunity.probability
                            / 100.0
                        ),
                        0,
                    )
                ),
                SalesOpportunity,
            )
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.status == OPEN_OPP_STATUS,
                SalesOpportunity.estimated_amount.isnot(None),
            )
            .scalar()
            or 0
        )

        overdue_tasks = (
            soft_alive(self.db.query(func.count(SalesTask.id)), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.status.in_(ACTIVE_TASK_STATUSES),
                SalesTask.due_at.isnot(None),
                SalesTask.due_at < now,
            )
            .scalar()
            or 0
        )

        activities_today = (
            soft_alive(self.db.query(func.count(SalesActivity.id)), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.activity_type.in_(ACTIVITY_TYPES),
                SalesActivity.activity_at >= today_start,
                SalesActivity.activity_at <= today_end,
            )
            .scalar()
            or 0
        )

        return SalesDashboardSummaryOut(
            open_leads=int(open_leads),
            open_opportunities=int(open_opps),
            pipeline_value=Decimal(str(pipeline_value)),
            weighted_pipeline_value=Decimal(str(weighted)).quantize(Decimal("0.01")),
            won_opportunities=int(won),
            lost_opportunities=int(lost),
            overdue_tasks=int(overdue_tasks),
            activities_today=int(activities_today),
        )

    def _pipeline_overview(
        self, organization_id: int, pipeline: SalesPipeline
    ) -> SalesPipelineOverviewOut:
        stages = (
            soft_alive(self.db.query(SalesPipelineStage), SalesPipelineStage)
            .filter(
                SalesPipelineStage.organization_id == organization_id,
                SalesPipelineStage.pipeline_id == pipeline.id,
                SalesPipelineStage.is_active.is_(True),
            )
            .order_by(SalesPipelineStage.position.asc())
            .all()
        )

        # Aggregate open opportunities by stage
        rows = (
            soft_alive(
                self.db.query(
                    SalesOpportunity.stage_id,
                    func.count(SalesOpportunity.id),
                    func.coalesce(func.sum(SalesOpportunity.estimated_amount), 0),
                    func.coalesce(func.avg(SalesOpportunity.probability), 0),
                ),
                SalesOpportunity,
            )
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.pipeline_id == pipeline.id,
                SalesOpportunity.status == OPEN_OPP_STATUS,
            )
            .group_by(SalesOpportunity.stage_id)
            .all()
        )
        by_stage = {
            int(stage_id): (int(cnt), Decimal(str(amount)), float(avg_prob or 0))
            for stage_id, cnt, amount, avg_prob in rows
        }

        stage_outs: list[SalesPipelineStageOverviewOut] = []
        for stage in stages:
            cnt, amount, avg_prob = by_stage.get(stage.id, (0, Decimal("0"), 0.0))
            # Closed won/lost stages still show count of matching status if needed
            if stage.is_won:
                cnt = (
                    soft_alive(self.db.query(func.count(SalesOpportunity.id)), SalesOpportunity)
                    .filter(
                        SalesOpportunity.organization_id == organization_id,
                        SalesOpportunity.stage_id == stage.id,
                        SalesOpportunity.status == WON_OPP_STATUS,
                    )
                    .scalar()
                    or 0
                )
                amount = (
                    soft_alive(
                        self.db.query(func.coalesce(func.sum(SalesOpportunity.estimated_amount), 0)),
                        SalesOpportunity,
                    )
                    .filter(
                        SalesOpportunity.organization_id == organization_id,
                        SalesOpportunity.stage_id == stage.id,
                        SalesOpportunity.status == WON_OPP_STATUS,
                    )
                    .scalar()
                    or 0
                )
                avg_prob = 100.0 if cnt else 0.0
                amount = Decimal(str(amount))
            elif stage.is_lost:
                cnt = (
                    soft_alive(self.db.query(func.count(SalesOpportunity.id)), SalesOpportunity)
                    .filter(
                        SalesOpportunity.organization_id == organization_id,
                        SalesOpportunity.stage_id == stage.id,
                        SalesOpportunity.status == LOST_OPP_STATUS,
                    )
                    .scalar()
                    or 0
                )
                amount = (
                    soft_alive(
                        self.db.query(func.coalesce(func.sum(SalesOpportunity.estimated_amount), 0)),
                        SalesOpportunity,
                    )
                    .filter(
                        SalesOpportunity.organization_id == organization_id,
                        SalesOpportunity.stage_id == stage.id,
                        SalesOpportunity.status == LOST_OPP_STATUS,
                    )
                    .scalar()
                    or 0
                )
                avg_prob = 0.0
                amount = Decimal(str(amount))

            stage_outs.append(
                SalesPipelineStageOverviewOut(
                    stage_id=stage.id,
                    code=stage.code,
                    name=stage.name,
                    position=stage.position,
                    probability=stage.probability,
                    is_won=stage.is_won,
                    is_lost=stage.is_lost,
                    opportunity_count=int(cnt),
                    amount_total=amount if isinstance(amount, Decimal) else Decimal(str(amount)),
                    average_probability=round(float(avg_prob), 1),
                )
            )

        return SalesPipelineOverviewOut(
            pipeline_id=pipeline.id,
            pipeline_name=pipeline.name,
            stages=stage_outs,
        )

    def _activities(self, organization_id: int) -> SalesDashboardActivitiesOut:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        week_end = today + timedelta(days=(6 - today.weekday()))
        today_start, today_end = _day_bounds(today)
        tom_start, tom_end = _day_bounds(tomorrow)
        _, week_end_dt = _day_bounds(week_end)

        def fetch(start: datetime, end: datetime, bucket: str) -> list[SalesDashboardActivityOut]:
            rows = (
                soft_alive(self.db.query(SalesActivity), SalesActivity)
                .filter(
                    SalesActivity.organization_id == organization_id,
                    SalesActivity.activity_type.in_(ACTIVITY_TYPES),
                    SalesActivity.activity_at >= start,
                    SalesActivity.activity_at <= end,
                )
                .order_by(SalesActivity.activity_at.asc())
                .limit(MAX_ACTIVITIES_PER_BUCKET)
                .all()
            )
            return [
                SalesDashboardActivityOut(
                    id=r.id,
                    activity_type=r.activity_type,
                    subject=r.subject,
                    activity_at=r.activity_at,
                    bucket=bucket,
                    result=r.result,
                    opportunity_id=r.opportunity_id,
                    company_id=r.company_id,
                    owner_user_id=r.owner_user_id,
                )
                for r in rows
            ]

        today_items = fetch(today_start, today_end, "today")
        tomorrow_items = fetch(tom_start, tom_end, "tomorrow")
        # this_week excludes today/tomorrow already shown? Spec says "Cette semaine" — include rest of week after tomorrow
        week_items = (
            soft_alive(self.db.query(SalesActivity), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.activity_type.in_(ACTIVITY_TYPES),
                SalesActivity.activity_at > tom_end,
                SalesActivity.activity_at <= week_end_dt,
            )
            .order_by(SalesActivity.activity_at.asc())
            .limit(MAX_ACTIVITIES_PER_BUCKET)
            .all()
        )
        this_week = [
            SalesDashboardActivityOut(
                id=r.id,
                activity_type=r.activity_type,
                subject=r.subject,
                activity_at=r.activity_at,
                bucket="this_week",
                result=r.result,
                opportunity_id=r.opportunity_id,
                company_id=r.company_id,
                owner_user_id=r.owner_user_id,
            )
            for r in week_items
        ]

        return SalesDashboardActivitiesOut(
            today=today_items,
            tomorrow=tomorrow_items,
            this_week=this_week,
        )

    def _tasks(self, organization_id: int) -> SalesDashboardTasksOut:
        today = date.today()
        today_start, today_end = _day_bounds(today)

        def map_task(r: SalesTask, bucket: str) -> SalesDashboardTaskOut:
            return SalesDashboardTaskOut(
                id=r.id,
                title=r.title,
                status=r.status,
                priority=r.priority,
                due_at=r.due_at,
                bucket=bucket,
                assignee_user_id=r.assignee_user_id,
                opportunity_id=r.opportunity_id,
                company_id=r.company_id,
            )

        overdue = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.status.in_(ACTIVE_TASK_STATUSES),
                SalesTask.due_at.isnot(None),
                SalesTask.due_at < today_start,
            )
            .order_by(SalesTask.due_at.asc())
            .limit(MAX_TASKS_PER_BUCKET)
            .all()
        )

        today_tasks = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.status.in_(ACTIVE_TASK_STATUSES),
                SalesTask.due_at.isnot(None),
                SalesTask.due_at >= today_start,
                SalesTask.due_at <= today_end,
            )
            .order_by(SalesTask.due_at.asc())
            .limit(MAX_TASKS_PER_BUCKET)
            .all()
        )

        upcoming = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.status.in_(ACTIVE_TASK_STATUSES),
                SalesTask.due_at.isnot(None),
                SalesTask.due_at > today_end,
            )
            .order_by(SalesTask.due_at.asc())
            .limit(MAX_TASKS_PER_BUCKET)
            .all()
        )

        return SalesDashboardTasksOut(
            overdue=[map_task(r, "overdue") for r in overdue],
            today=[map_task(r, "today") for r in today_tasks],
            upcoming=[map_task(r, "upcoming") for r in upcoming],
        )

    def _recent_opportunities(self, organization_id: int) -> list[SalesDashboardOpportunityOut]:
        rows = (
            soft_alive(
                self.db.query(SalesOpportunity, SalesPipelineStage.name, SalesCompany.name),
                SalesOpportunity,
            )
            .outerjoin(
                SalesPipelineStage,
                SalesPipelineStage.id == SalesOpportunity.stage_id,
            )
            .outerjoin(SalesCompany, SalesCompany.id == SalesOpportunity.company_id)
            .filter(SalesOpportunity.organization_id == organization_id)
            .order_by(SalesOpportunity.updated_at.desc())
            .limit(MAX_RECENT_OPPORTUNITIES)
            .all()
        )
        out: list[SalesDashboardOpportunityOut] = []
        for opp, stage_name, company_name in rows:
            out.append(
                SalesDashboardOpportunityOut(
                    id=opp.id,
                    name=opp.name,
                    estimated_amount=opp.estimated_amount,
                    probability=opp.probability,
                    stage_id=opp.stage_id,
                    stage_name=stage_name,
                    status=opp.status,
                    owner_user_id=opp.owner_user_id,
                    company_id=opp.company_id,
                    company_name=company_name,
                    updated_at=opp.updated_at,
                )
            )
        return out
