"""SalesPipelineService — board aggregation, health/risk/aging, stage moves.

All commercial math is server-side. Frontend displays only.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models_saas import User
from app.sales_crm.pipeline_schemas import (
    PipelineBoardOut,
    PipelineBoardSummaryOut,
    PipelineCardOut,
    PipelineColumnOut,
    PipelineDrawerActivityOut,
    PipelineDrawerNoteOut,
    PipelineDrawerOut,
    PipelineDrawerPersonOut,
    PipelineDrawerTaskOut,
)
from app.sales_crm.models import (
    SalesActivity,
    SalesCompany,
    SalesNote,
    SalesOpportunity,
    SalesPerson,
    SalesPipeline,
    SalesPipelineStage,
    SalesTask,
)
from app.sales_crm.service import (
    ensure_default_pipeline,
    get_org_row,
    soft_alive,
    update_opportunity,
)

ACTIVE_TASK = ("todo", "in_progress")
ACTIVITY_TYPES = ("call", "email", "meeting", "visit")


def _now() -> datetime:
    return datetime.utcnow()


def days_in_stage(entered: datetime | None, now: datetime | None = None) -> int:
    ref = now or _now()
    if not entered:
        return 0
    delta = ref - entered
    return max(0, delta.days)


def aging_label(days: int) -> str:
    if days <= 0:
        return "Aujourd'hui"
    if days <= 3:
        return f"{days} jour" + ("s" if days > 1 else "")
    if days <= 12:
        return f"{days} jours"
    if days <= 48:
        return f"{days} jours"
    return f"{days} jours"


def health_score_for(
    *,
    days: int,
    has_contact: bool,
    has_company: bool,
    last_activity_at: datetime | None,
    next_activity_at: datetime | None,
    has_open_task: bool,
    probability: int,
    stage_probability: int,
    now: datetime | None = None,
) -> tuple[int, str]:
    """Deterministic 0–100 health — no AI."""
    ref = now or _now()
    score = 45
    if has_contact:
        score += 10
    if has_company:
        score += 5
    if last_activity_at and (ref - last_activity_at).days <= 7:
        score += 15
    elif last_activity_at and (ref - last_activity_at).days <= 14:
        score += 5
    elif not last_activity_at:
        score -= 15
    if next_activity_at and next_activity_at >= ref:
        score += 15
    if has_open_task:
        score += 10
    else:
        score -= 10
    # probability coherence vs stage default
    if abs(probability - stage_probability) <= 15:
        score += 5
    else:
        score -= 5
    if days >= 30:
        score -= 20
    elif days >= 14:
        score -= 10
    elif days >= 7:
        score -= 5
    score = max(0, min(100, score))
    if score >= 80:
        label = "Excellent"
    elif score >= 60:
        label = "Bon"
    elif score >= 40:
        label = "À surveiller"
    else:
        label = "Critique"
    return score, label


def risk_level_for(
    *,
    days: int,
    last_activity_at: datetime | None,
    expected_close: date | None,
    probability: int,
    health: int,
    now: datetime | None = None,
) -> tuple[str, str]:
    ref = now or _now()
    labels = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critique",
    }
    level = "low"
    if days >= 45 or health < 35:
        level = "critical"
    elif days >= 21 or (last_activity_at and (ref - last_activity_at).days >= 21):
        level = "high"
    elif days >= 10 or probability < 20:
        level = "medium"
    if expected_close and expected_close < ref.date() and level in ("low", "medium"):
        level = "high"
    return level, labels[level]


class SalesPipelineService:
    def __init__(self, db: Session):
        self.db = db

    def build_board(
        self, *, organization_id: int, user_id: int | None = None, pipeline_id: int | None = None
    ) -> PipelineBoardOut:
        if pipeline_id:
            pipeline = get_org_row(
                self.db, SalesPipeline, organization_id=organization_id, row_id=pipeline_id
            )
        else:
            pipeline = ensure_default_pipeline(
                self.db, organization_id=organization_id, user_id=user_id
            )
            self.db.flush()

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

        opps = (
            soft_alive(self.db.query(SalesOpportunity), SalesOpportunity)
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.pipeline_id == pipeline.id,
            )
            .order_by(SalesOpportunity.updated_at.desc())
            .all()
        )

        company_ids = {o.company_id for o in opps if o.company_id}
        person_ids = {o.person_id for o in opps if o.person_id}
        owner_ids = {o.owner_user_id for o in opps if o.owner_user_id}
        opp_ids = [o.id for o in opps]

        companies = {
            c.id: c
            for c in soft_alive(self.db.query(SalesCompany), SalesCompany)
            .filter(SalesCompany.organization_id == organization_id, SalesCompany.id.in_(company_ids or [-1]))
            .all()
        }
        people = {
            p.id: p
            for p in soft_alive(self.db.query(SalesPerson), SalesPerson)
            .filter(SalesPerson.organization_id == organization_id, SalesPerson.id.in_(person_ids or [-1]))
            .all()
        }
        owners = {
            u.id: u
            for u in self.db.query(User).filter(User.id.in_(owner_ids or [-1])).all()
        }

        # Activities / tasks keyed by opportunity
        last_act: dict[int, SalesActivity] = {}
        next_act: dict[int, SalesActivity] = {}
        open_tasks: set[int] = set()
        now = _now()

        if opp_ids:
            acts = (
                soft_alive(self.db.query(SalesActivity), SalesActivity)
                .filter(
                    SalesActivity.organization_id == organization_id,
                    SalesActivity.opportunity_id.in_(opp_ids),
                    SalesActivity.activity_type.in_(ACTIVITY_TYPES),
                )
                .order_by(SalesActivity.activity_at.desc())
                .all()
            )
            for a in acts:
                oid = a.opportunity_id
                if oid is None:
                    continue
                if oid not in last_act and a.activity_at <= now:
                    last_act[oid] = a
                if a.activity_at > now and (oid not in next_act or a.activity_at < next_act[oid].activity_at):
                    next_act[oid] = a

            tasks = (
                soft_alive(self.db.query(SalesTask), SalesTask)
                .filter(
                    SalesTask.organization_id == organization_id,
                    SalesTask.opportunity_id.in_(opp_ids),
                    SalesTask.status.in_(ACTIVE_TASK),
                )
                .all()
            )
            for t in tasks:
                if t.opportunity_id:
                    open_tasks.add(t.opportunity_id)

        stage_by_id = {s.id: s for s in stages}
        cards_by_stage: dict[int, list[PipelineCardOut]] = {s.id: [] for s in stages}

        critical_count = 0
        open_count = 0
        pipeline_value = Decimal("0")
        weighted = Decimal("0")
        won_count = 0
        lost_count = 0

        for opp in opps:
            stage = stage_by_id.get(opp.stage_id)
            if not stage:
                continue
            entered = opp.stage_entered_at or opp.created_at
            days = days_in_stage(entered, now)
            company = companies.get(opp.company_id) if opp.company_id else None
            person = people.get(opp.person_id) if opp.person_id else None
            owner = owners.get(opp.owner_user_id) if opp.owner_user_id else None
            la = last_act.get(opp.id)
            na = next_act.get(opp.id)
            has_task = opp.id in open_tasks

            score, health_label = health_score_for(
                days=days,
                has_contact=person is not None,
                has_company=company is not None,
                last_activity_at=la.activity_at if la else None,
                next_activity_at=na.activity_at if na else None,
                has_open_task=has_task,
                probability=opp.probability,
                stage_probability=stage.probability,
                now=now,
            )
            risk, risk_label = risk_level_for(
                days=days,
                last_activity_at=la.activity_at if la else None,
                expected_close=opp.expected_close_date,
                probability=opp.probability,
                health=score,
                now=now,
            )
            if risk == "critical":
                critical_count += 1

            badges: list[str] = []
            if opp.priority == "high":
                badges.append("Priorité haute")
            if risk in ("high", "critical"):
                badges.append(risk_label)
            if days >= 14:
                badges.append("Aging")

            contact_name = None
            if person:
                contact_name = f"{person.first_name} {person.last_name}".strip()
            owner_label = None
            if owner:
                owner_label = f"{owner.first_name or ''} {owner.last_name or ''}".strip() or owner.email

            card = PipelineCardOut(
                id=opp.id,
                name=opp.name,
                company_id=opp.company_id,
                company_name=company.name if company else None,
                estimated_amount=opp.estimated_amount,
                person_id=opp.person_id,
                contact_name=contact_name,
                owner_user_id=opp.owner_user_id,
                owner_label=owner_label,
                probability=opp.probability,
                priority=opp.priority,
                source=opp.source,
                status=opp.status,
                stage_id=opp.stage_id,
                stage_entered_at=entered,
                days_in_stage=days,
                aging_label=aging_label(days),
                last_activity_at=la.activity_at if la else None,
                last_activity_subject=la.subject if la else None,
                next_activity_at=na.activity_at if na else None,
                next_activity_subject=na.subject if na else None,
                health_score=score,
                health_label=health_label,
                risk_level=risk,
                risk_label=risk_label,
                expected_close_date=opp.expected_close_date,
                badges=badges,
                updated_at=opp.updated_at,
            )
            cards_by_stage.setdefault(stage.id, []).append(card)

            if stage.is_won or opp.status == "won":
                won_count += 1
            elif stage.is_lost or opp.status == "lost":
                lost_count += 1
            else:
                open_count += 1
                if opp.estimated_amount:
                    pipeline_value += Decimal(str(opp.estimated_amount))
                    weighted += Decimal(str(opp.estimated_amount)) * Decimal(opp.probability) / Decimal(100)

        columns: list[PipelineColumnOut] = []
        for stage in stages:
            cards = cards_by_stage.get(stage.id, [])
            amount = sum((c.estimated_amount or Decimal("0")) for c in cards)
            w_amount = sum(
                ((c.estimated_amount or Decimal("0")) * Decimal(c.probability) / Decimal(100))
                for c in cards
            )
            avg_prob = (
                sum(c.probability for c in cards) / len(cards) if cards else float(stage.probability)
            )
            avg_days = sum(c.days_in_stage for c in cards) / len(cards) if cards else 0.0
            columns.append(
                PipelineColumnOut(
                    stage_id=stage.id,
                    code=stage.code,
                    name=stage.name,
                    position=stage.position,
                    probability=stage.probability,
                    is_won=stage.is_won,
                    is_lost=stage.is_lost,
                    opportunity_count=len(cards),
                    amount_total=amount,
                    weighted_amount=w_amount.quantize(Decimal("0.01")) if isinstance(w_amount, Decimal) else Decimal(str(w_amount)),
                    average_probability=round(float(avg_prob), 1),
                    average_days_in_stage=round(float(avg_days), 1),
                    cards=cards,
                )
            )

        return PipelineBoardOut(
            pipeline_id=pipeline.id,
            pipeline_name=pipeline.name,
            pipeline_code=pipeline.code,
            stages=columns,
            summary=PipelineBoardSummaryOut(
                open_opportunities=open_count,
                pipeline_value=pipeline_value,
                weighted_pipeline_value=weighted.quantize(Decimal("0.01")),
                won_count=won_count,
                lost_count=lost_count,
                critical_count=critical_count,
            ),
            generated_at=now,
        )

    def move_stage(
        self,
        *,
        organization_id: int,
        user_id: int | None,
        opportunity_id: int,
        stage_id: int,
        expected_stage_id: int | None = None,
    ) -> PipelineCardOut:
        row = get_org_row(
            self.db, SalesOpportunity, organization_id=organization_id, row_id=opportunity_id
        )
        if expected_stage_id is not None and row.stage_id != expected_stage_id:
            raise HTTPException(
                409,
                detail={
                    "code": "stage_conflict",
                    "message": "L'opportunité a changé d'étape — actualisez le pipeline.",
                    "current_stage_id": row.stage_id,
                },
            )
        target = get_org_row(
            self.db, SalesPipelineStage, organization_id=organization_id, row_id=stage_id
        )
        if target.pipeline_id != row.pipeline_id:
            raise HTTPException(
                400,
                detail={"code": "stage_mismatch", "message": "Étape hors pipeline"},
            )
        update_opportunity(
            self.db,
            organization_id=organization_id,
            user_id=user_id,
            opportunity_id=opportunity_id,
            data={"stage_id": stage_id},
        )
        board = self.build_board(
            organization_id=organization_id, user_id=user_id, pipeline_id=row.pipeline_id
        )
        for col in board.stages:
            for card in col.cards:
                if card.id == opportunity_id:
                    return card
        raise HTTPException(404, detail={"code": "not_found", "message": "Carte introuvable après move"})

    def drawer(
        self, *, organization_id: int, user_id: int | None, opportunity_id: int
    ) -> PipelineDrawerOut:
        board = self.build_board(organization_id=organization_id, user_id=user_id)
        card: PipelineCardOut | None = None
        stage_name = ""
        for col in board.stages:
            for c in col.cards:
                if c.id == opportunity_id:
                    card = c
                    stage_name = col.name
                    break
            if card:
                break
        if not card:
            # maybe filtered — load raw
            raise HTTPException(404, detail={"code": "not_found", "message": "Opportunité introuvable"})

        opp = get_org_row(
            self.db, SalesOpportunity, organization_id=organization_id, row_id=opportunity_id
        )
        contacts: list[PipelineDrawerPersonOut] = []
        if opp.company_id:
            people = (
                soft_alive(self.db.query(SalesPerson), SalesPerson)
                .filter(
                    SalesPerson.organization_id == organization_id,
                    SalesPerson.company_id == opp.company_id,
                )
                .limit(10)
                .all()
            )
            contacts = [
                PipelineDrawerPersonOut(
                    id=p.id,
                    first_name=p.first_name,
                    last_name=p.last_name,
                    email=p.email,
                    phone=p.phone,
                    job_title=p.job_title,
                )
                for p in people
            ]
        elif opp.person_id:
            p = soft_alive(self.db.query(SalesPerson), SalesPerson).filter(
                SalesPerson.id == opp.person_id,
                SalesPerson.organization_id == organization_id,
            ).first()
            if p:
                contacts = [
                    PipelineDrawerPersonOut(
                        id=p.id,
                        first_name=p.first_name,
                        last_name=p.last_name,
                        email=p.email,
                        phone=p.phone,
                        job_title=p.job_title,
                    )
                ]

        activities = (
            soft_alive(self.db.query(SalesActivity), SalesActivity)
            .filter(
                SalesActivity.organization_id == organization_id,
                SalesActivity.opportunity_id == opportunity_id,
            )
            .order_by(SalesActivity.activity_at.desc())
            .limit(20)
            .all()
        )
        tasks = (
            soft_alive(self.db.query(SalesTask), SalesTask)
            .filter(
                SalesTask.organization_id == organization_id,
                SalesTask.opportunity_id == opportunity_id,
            )
            .order_by(SalesTask.due_at.asc())
            .limit(20)
            .all()
        )
        notes = (
            soft_alive(self.db.query(SalesNote), SalesNote)
            .filter(
                SalesNote.organization_id == organization_id,
                SalesNote.entity_type == "opportunity",
                SalesNote.entity_id == opportunity_id,
            )
            .order_by(SalesNote.created_at.desc())
            .limit(20)
            .all()
        )

        return PipelineDrawerOut(
            opportunity=card,
            company_name=card.company_name,
            contacts=contacts,
            activities=[
                PipelineDrawerActivityOut(
                    id=a.id,
                    activity_type=a.activity_type,
                    subject=a.subject,
                    activity_at=a.activity_at,
                    result=a.result,
                )
                for a in activities
            ],
            tasks=[
                PipelineDrawerTaskOut(
                    id=t.id,
                    title=t.title,
                    status=t.status,
                    priority=t.priority,
                    due_at=t.due_at,
                )
                for t in tasks
            ],
            notes=[
                PipelineDrawerNoteOut(
                    id=n.id,
                    body_markdown=n.body_markdown,
                    author_user_id=n.author_user_id,
                    created_at=n.created_at,
                )
                for n in notes
            ],
            stage_id=card.stage_id,
            stage_name=stage_name,
            amount=card.estimated_amount,
            probability=card.probability,
            quick_actions=[
                {"id": "activity", "label": "Nouvelle activité", "href": "/sales/activities"},
                {"id": "task", "label": "Nouvelle tâche", "href": "/sales/tasks"},
                {"id": "note", "label": "Ajouter une note", "href": "/sales/pipeline"},
                {"id": "open", "label": "Ouvrir la fiche", "href": f"/sales/pipeline?id={opportunity_id}"},
            ],
        )
