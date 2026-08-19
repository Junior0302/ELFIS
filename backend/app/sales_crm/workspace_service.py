"""RelationshipWorkspaceService — unified CRM workspace aggregation (S1.4).

One architecture for lead | company | person | opportunity.
All scores and timeline ordering are server-side.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_saas import User
from app.models_vault import VaultDocument
from app.sales_crm.models import (
    SalesActivity,
    SalesAttachment,
    SalesCompany,
    SalesLead,
    SalesNote,
    SalesOpportunity,
    SalesPerson,
    SalesPipeline,
    SalesPipelineStage,
    SalesTask,
)
from app.sales_crm.pipeline_service import (
    days_in_stage,
    health_score_for,
    risk_level_for,
)
from app.sales_crm.service import get_org_row, soft_alive
from app.sales_crm.workspace_schemas import (
    RelationshipWorkspaceOut,
    WorkspaceActivityOut,
    WorkspaceAttachmentOut,
    WorkspaceContactOut,
    WorkspaceEntity,
    WorkspaceHeaderOut,
    WorkspaceHealthOut,
    WorkspaceNoteOut,
    WorkspaceOpportunityOut,
    WorkspaceQuickActionOut,
    WorkspaceRelationshipOut,
    WorkspaceSummaryOut,
    WorkspaceTaskOut,
    WorkspaceTimelineItemOut,
)

ACTIVE_TASK = ("todo", "in_progress")
ACTIVITY_TYPES = ("call", "email", "meeting", "visit", "task", "note")
VALID_ENTITIES = frozenset({"lead", "company", "person", "opportunity"})


def _now() -> datetime:
    return datetime.utcnow()


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    return datetime.combine(d, time.min), datetime.combine(d, time.max)


def relationship_score_for(
    *,
    activities_count: int,
    last_activity_at: datetime | None,
    contacts_count: int,
    has_email: bool,
    has_phone: bool,
    has_company: bool,
    created_at: datetime | None,
    now: datetime | None = None,
) -> tuple[int, str, str, list[str]]:
    """Deterministic relationship score 0–100 — no AI."""
    ref = now or _now()
    score = 30
    factors: list[str] = []

    if activities_count >= 10:
        score += 25
        factors.append("Activité dense")
    elif activities_count >= 4:
        score += 15
        factors.append("Activité régulière")
    elif activities_count >= 1:
        score += 8
        factors.append("Quelques interactions")
    else:
        score -= 10
        factors.append("Aucune activité")

    if last_activity_at:
        age = (ref - last_activity_at).days
        if age <= 7:
            score += 20
            factors.append("Contact récent")
        elif age <= 21:
            score += 10
            factors.append("Contact dans le mois")
        elif age <= 60:
            score += 0
        else:
            score -= 15
            factors.append("Relation inactive")
    else:
        score -= 10

    if contacts_count >= 3:
        score += 15
        factors.append("Plusieurs contacts")
    elif contacts_count >= 1:
        score += 8
        factors.append("Contact identifié")
    else:
        score -= 8
        factors.append("Pas de contact")

    completeness = 0
    if has_email:
        completeness += 1
    if has_phone:
        completeness += 1
    if has_company:
        completeness += 1
    score += completeness * 5
    if completeness >= 2:
        factors.append("Fiche relativement complète")

    if created_at:
        tenure = (ref - created_at).days
        if tenure >= 180:
            score += 10
            factors.append("Relation ancienne")
        elif tenure >= 30:
            score += 5

    score = max(0, min(100, score))
    if score >= 80:
        label = "Excellent"
    elif score >= 60:
        label = "Bon"
    elif score >= 40:
        label = "Correct"
    else:
        label = "Fragile"
    explanation = " · ".join(factors[:4]) if factors else "Données insuffisantes"
    return score, label, explanation, factors


class RelationshipWorkspaceService:
    def __init__(self, db: Session):
        self.db = db

    def build(
        self,
        *,
        organization_id: int,
        entity: str,
        entity_id: int,
        user_id: int | None = None,
        publish_opened: bool = True,
    ) -> RelationshipWorkspaceOut:
        entity = (entity or "").strip().lower()
        if entity not in VALID_ENTITIES:
            raise HTTPException(
                400,
                detail={"code": "invalid_entity", "message": "entity doit être lead|company|person|opportunity"},
            )

        ctx = self._resolve_context(organization_id=organization_id, entity=entity, entity_id=entity_id)
        now = _now()

        contacts = self._contacts(organization_id, ctx)
        opportunities = self._opportunities(organization_id, ctx, now)
        activities = self._activities(organization_id, ctx)
        tasks = self._tasks(organization_id, ctx, now)
        notes = self._notes(organization_id, ctx)
        attachments = self._attachments(organization_id, ctx)
        timeline = self._timeline(organization_id, ctx, now)

        last_activity_at = activities[0].activity_at if activities else None
        health, health_label, health_expl, risk, risk_label = self._health_bundle(ctx, activities, tasks, now)

        has_email = any(c.email for c in contacts) or bool(ctx.get("email"))
        has_phone = any(c.phone for c in contacts) or bool(ctx.get("phone"))
        rel_score, rel_label, rel_expl, rel_factors = relationship_score_for(
            activities_count=len(activities),
            last_activity_at=last_activity_at,
            contacts_count=len(contacts),
            has_email=has_email,
            has_phone=has_phone,
            has_company=bool(ctx.get("company_id") or entity == "company"),
            created_at=ctx.get("created_at"),
            now=now,
        )

        open_tasks = sum(1 for t in tasks if t.bucket in ("overdue", "today", "upcoming") and t.status in ACTIVE_TASK)
        pipeline_value = sum(
            (o.estimated_amount or Decimal("0")) for o in opportunities if o.status == "open"
        )

        summary = WorkspaceSummaryOut(
            open_opportunities=sum(1 for o in opportunities if o.status == "open"),
            contacts_count=len(contacts),
            activities_count=len(activities),
            open_tasks_count=open_tasks,
            notes_count=len(notes),
            documents_count=len(attachments),
            pipeline_value=pipeline_value if isinstance(pipeline_value, Decimal) else Decimal(str(pipeline_value)),
        )

        header = WorkspaceHeaderOut(
            entity=entity,  # type: ignore[arg-type]
            entity_id=entity_id,
            name=ctx["name"],
            status=ctx.get("status"),
            pipeline_name=ctx.get("pipeline_name"),
            stage_name=ctx.get("stage_name"),
            amount=ctx.get("amount"),
            owner_label=ctx.get("owner_label"),
            created_at=ctx.get("created_at"),
            last_activity_at=last_activity_at,
            health_score=health,
            health_label=health_label,
            health_explanation=health_expl,
            relationship_score=rel_score,
            relationship_label=rel_label,
            risk_level=risk,
            risk_label=risk_label,
        )

        out = RelationshipWorkspaceOut(
            header=header,
            summary=summary,
            contacts=contacts,
            opportunities=opportunities,
            activities=activities,
            tasks=tasks,
            notes=notes,
            attachments=attachments,
            timeline=timeline,
            health=WorkspaceHealthOut(
                score=health,
                label=health_label,
                explanation=health_expl,
                risk_level=risk,
                risk_label=risk_label,
            ),
            relationship=WorkspaceRelationshipOut(
                score=rel_score,
                label=rel_label,
                explanation=rel_expl,
                factors=rel_factors,
            ),
            quick_actions=self._quick_actions(entity, entity_id, ctx),
            generated_at=now,
        )

        if publish_opened:
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.SALES_WORKSPACE_OPENED,
                    organization_id=organization_id,
                    aggregate_type=f"sales_{entity}",
                    aggregate_id=str(entity_id),
                    payload={"entity": entity, "entity_id": entity_id},
                    metadata={
                        "source": "sales_crm",
                        "actor_user_id": str(user_id) if user_id else None,
                    },
                    idempotency_key=f"sales:workspace:opened:{organization_id}:{entity}:{entity_id}:{int(now.timestamp())}",
                ),
                commit=False,
            )
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.SALES_RELATIONSHIP_UPDATED,
                    organization_id=organization_id,
                    aggregate_type=f"sales_{entity}",
                    aggregate_id=str(entity_id),
                    payload={
                        "entity": entity,
                        "entity_id": entity_id,
                        "relationship_score": rel_score,
                        "health_score": health,
                    },
                    metadata={"source": "sales_crm"},
                    idempotency_key=f"sales:relationship:updated:{organization_id}:{entity}:{entity_id}:{rel_score}:{health}",
                ),
                commit=False,
            )
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.SALES_TIMELINE_UPDATED,
                    organization_id=organization_id,
                    aggregate_type=f"sales_{entity}",
                    aggregate_id=str(entity_id),
                    payload={
                        "entity": entity,
                        "entity_id": entity_id,
                        "timeline_count": len(timeline),
                    },
                    metadata={"source": "sales_crm"},
                    idempotency_key=f"sales:timeline:updated:{organization_id}:{entity}:{entity_id}:{len(timeline)}",
                ),
                commit=False,
            )

        return out

    def _resolve_context(self, *, organization_id: int, entity: str, entity_id: int) -> dict:
        owners_cache: dict[int, str] = {}

        def owner_label(uid: int | None) -> str | None:
            if not uid:
                return None
            if uid in owners_cache:
                return owners_cache[uid]
            u = self.db.get(User, uid)
            if not u:
                return None
            label = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
            owners_cache[uid] = label
            return label

        if entity == "lead":
            row = get_org_row(self.db, SalesLead, organization_id=organization_id, row_id=entity_id)
            return {
                "name": row.title,
                "status": row.status,
                "created_at": row.created_at,
                "owner_label": owner_label(row.owner_user_id),
                "amount": row.estimated_amount,
                "company_id": row.company_id,
                "person_id": row.person_id,
                "lead_id": row.id,
                "opportunity_ids": [row.converted_opportunity_id] if row.converted_opportunity_id else [],
                "email": row.email,
                "phone": row.phone,
                "owner_fn": owner_label,
            }

        if entity == "company":
            row = get_org_row(self.db, SalesCompany, organization_id=organization_id, row_id=entity_id)
            return {
                "name": row.name,
                "status": row.status,
                "created_at": row.created_at,
                "owner_label": owner_label(row.owner_user_id),
                "company_id": row.id,
                "person_id": None,
                "lead_id": None,
                "opportunity_ids": None,  # resolve by company
                "email": row.email,
                "phone": row.phone,
                "owner_fn": owner_label,
            }

        if entity == "person":
            row = get_org_row(self.db, SalesPerson, organization_id=organization_id, row_id=entity_id)
            return {
                "name": f"{row.first_name} {row.last_name}".strip(),
                "status": row.status,
                "created_at": row.created_at,
                "owner_label": owner_label(row.owner_user_id),
                "company_id": row.company_id,
                "person_id": row.id,
                "lead_id": None,
                "opportunity_ids": None,
                "email": row.email,
                "phone": row.phone,
                "owner_fn": owner_label,
            }

        # opportunity
        row = get_org_row(self.db, SalesOpportunity, organization_id=organization_id, row_id=entity_id)
        stage = (
            soft_alive(self.db.query(SalesPipelineStage), SalesPipelineStage)
            .filter(SalesPipelineStage.id == row.stage_id)
            .first()
        )
        pipe = (
            soft_alive(self.db.query(SalesPipeline), SalesPipeline)
            .filter(SalesPipeline.id == row.pipeline_id)
            .first()
        )
        return {
            "name": row.name,
            "status": row.status,
            "created_at": row.created_at,
            "owner_label": owner_label(row.owner_user_id),
            "amount": row.estimated_amount,
            "company_id": row.company_id,
            "person_id": row.person_id,
            "lead_id": row.lead_id,
            "opportunity_ids": [row.id],
            "pipeline_name": pipe.name if pipe else None,
            "stage_name": stage.name if stage else None,
            "stage_probability": stage.probability if stage else 0,
            "stage_entered_at": row.stage_entered_at or row.created_at,
            "probability": row.probability,
            "expected_close_date": row.expected_close_date,
            "opp_row": row,
            "owner_fn": owner_label,
        }

    def _scope_filter_ids(self, organization_id: int, ctx: dict) -> dict:
        """Resolve related opportunity / company / person / lead ids for queries."""
        company_id = ctx.get("company_id")
        person_id = ctx.get("person_id")
        lead_id = ctx.get("lead_id")
        opp_ids = ctx.get("opportunity_ids")

        if opp_ids is None:
            q = soft_alive(self.db.query(SalesOpportunity), SalesOpportunity).filter(
                SalesOpportunity.organization_id == organization_id
            )
            if company_id:
                q = q.filter(SalesOpportunity.company_id == company_id)
            elif person_id:
                q = q.filter(SalesOpportunity.person_id == person_id)
            elif lead_id:
                q = q.filter(SalesOpportunity.lead_id == lead_id)
            else:
                q = q.filter(SalesOpportunity.id == -1)
            opp_ids = [o.id for o in q.all()]

        return {
            "company_id": company_id,
            "person_id": person_id,
            "lead_id": lead_id,
            "opportunity_ids": opp_ids,
        }

    def _contacts(self, organization_id: int, ctx: dict) -> list[WorkspaceContactOut]:
        scope = self._scope_filter_ids(organization_id, ctx)
        people: list[SalesPerson] = []
        if scope["person_id"]:
            p = (
                soft_alive(self.db.query(SalesPerson), SalesPerson)
                .filter(
                    SalesPerson.organization_id == organization_id,
                    SalesPerson.id == scope["person_id"],
                )
                .first()
            )
            if p:
                people = [p]
        if scope["company_id"]:
            more = (
                soft_alive(self.db.query(SalesPerson), SalesPerson)
                .filter(
                    SalesPerson.organization_id == organization_id,
                    SalesPerson.company_id == scope["company_id"],
                )
                .order_by(SalesPerson.last_name.asc())
                .limit(50)
                .all()
            )
            seen = {p.id for p in people}
            for p in more:
                if p.id not in seen:
                    people.append(p)
        primary_id = scope["person_id"]
        return [
            WorkspaceContactOut(
                id=p.id,
                first_name=p.first_name,
                last_name=p.last_name,
                email=p.email,
                phone=p.phone,
                job_title=p.job_title,
                is_primary=bool(primary_id and p.id == primary_id),
                linkedin_url=None,
            )
            for p in people
        ]

    def _opportunities(
        self, organization_id: int, ctx: dict, now: datetime
    ) -> list[WorkspaceOpportunityOut]:
        scope = self._scope_filter_ids(organization_id, ctx)
        ids = scope["opportunity_ids"] or []
        if not ids:
            return []
        rows = (
            soft_alive(self.db.query(SalesOpportunity), SalesOpportunity)
            .filter(
                SalesOpportunity.organization_id == organization_id,
                SalesOpportunity.id.in_(ids),
            )
            .order_by(SalesOpportunity.updated_at.desc())
            .limit(50)
            .all()
        )
        stage_ids = {r.stage_id for r in rows}
        stages = {
            s.id: s
            for s in soft_alive(self.db.query(SalesPipelineStage), SalesPipelineStage)
            .filter(SalesPipelineStage.id.in_(stage_ids or [-1]))
            .all()
        }
        owner_fn = ctx["owner_fn"]
        out: list[WorkspaceOpportunityOut] = []
        for r in rows:
            stage = stages.get(r.stage_id)
            days = days_in_stage(r.stage_entered_at or r.created_at, now)
            score, label = health_score_for(
                days=days,
                has_contact=bool(r.person_id),
                has_company=bool(r.company_id),
                last_activity_at=None,
                next_activity_at=None,
                has_open_task=False,
                probability=r.probability,
                stage_probability=stage.probability if stage else r.probability,
                now=now,
            )
            out.append(
                WorkspaceOpportunityOut(
                    id=r.id,
                    name=r.name,
                    stage_name=stage.name if stage else None,
                    estimated_amount=r.estimated_amount,
                    probability=r.probability,
                    owner_label=owner_fn(r.owner_user_id),
                    health_score=score,
                    health_label=label,
                    status=r.status,
                    href=f"/sales/deals/{r.id}",
                )
            )
        return out

    def _activities(self, organization_id: int, ctx: dict) -> list[WorkspaceActivityOut]:
        scope = self._scope_filter_ids(organization_id, ctx)
        q = soft_alive(self.db.query(SalesActivity), SalesActivity).filter(
            SalesActivity.organization_id == organization_id,
            SalesActivity.activity_type.in_(ACTIVITY_TYPES),
        )
        clauses = []
        if scope["opportunity_ids"]:
            clauses.append(SalesActivity.opportunity_id.in_(scope["opportunity_ids"]))
        if scope["company_id"]:
            clauses.append(SalesActivity.company_id == scope["company_id"])
        if scope["person_id"]:
            clauses.append(SalesActivity.person_id == scope["person_id"])
        if scope["lead_id"]:
            clauses.append(SalesActivity.lead_id == scope["lead_id"])
        if not clauses:
            return []
        from sqlalchemy import or_

        rows = q.filter(or_(*clauses)).order_by(SalesActivity.activity_at.desc()).limit(40).all()
        owner_fn = ctx["owner_fn"]
        return [
            WorkspaceActivityOut(
                id=a.id,
                activity_type=a.activity_type,
                subject=a.subject,
                activity_at=a.activity_at,
                result=a.result,
                owner_label=owner_fn(a.owner_user_id),
            )
            for a in rows
        ]

    def _tasks(self, organization_id: int, ctx: dict, now: datetime) -> list[WorkspaceTaskOut]:
        scope = self._scope_filter_ids(organization_id, ctx)
        q = soft_alive(self.db.query(SalesTask), SalesTask).filter(
            SalesTask.organization_id == organization_id
        )
        from sqlalchemy import or_

        clauses = []
        if scope["opportunity_ids"]:
            clauses.append(SalesTask.opportunity_id.in_(scope["opportunity_ids"]))
        if scope["company_id"]:
            clauses.append(SalesTask.company_id == scope["company_id"])
        if scope["person_id"]:
            clauses.append(SalesTask.person_id == scope["person_id"])
        if not clauses:
            return []
        rows = q.filter(or_(*clauses)).order_by(SalesTask.due_at.asc()).limit(40).all()
        today = now.date()
        today_start, today_end = _day_bounds(today)
        out: list[WorkspaceTaskOut] = []
        for t in rows:
            bucket = "other"
            if t.due_at:
                if t.due_at < today_start and t.status in ACTIVE_TASK:
                    bucket = "overdue"
                elif today_start <= t.due_at <= today_end:
                    bucket = "today"
                elif t.due_at > today_end and t.status in ACTIVE_TASK:
                    bucket = "upcoming"
            out.append(
                WorkspaceTaskOut(
                    id=t.id,
                    title=t.title,
                    status=t.status,
                    priority=t.priority,
                    due_at=t.due_at,
                    bucket=bucket,
                )
            )
        # overdue first
        order = {"overdue": 0, "today": 1, "upcoming": 2, "other": 3}
        out.sort(key=lambda x: order.get(x.bucket, 9))
        return out

    def _notes(self, organization_id: int, ctx: dict) -> list[WorkspaceNoteOut]:
        scope = self._scope_filter_ids(organization_id, ctx)
        from sqlalchemy import or_

        filters = []
        if scope["company_id"]:
            filters.append(
                (SalesNote.entity_type == "company") & (SalesNote.entity_id == scope["company_id"])
            )
        if scope["person_id"]:
            filters.append(
                (SalesNote.entity_type == "person") & (SalesNote.entity_id == scope["person_id"])
            )
        if scope["lead_id"]:
            filters.append(
                (SalesNote.entity_type == "lead") & (SalesNote.entity_id == scope["lead_id"])
            )
        for oid in scope["opportunity_ids"] or []:
            filters.append((SalesNote.entity_type == "opportunity") & (SalesNote.entity_id == oid))
        if not filters:
            return []
        rows = (
            soft_alive(self.db.query(SalesNote), SalesNote)
            .filter(SalesNote.organization_id == organization_id)
            .filter(or_(*filters))
            .order_by(SalesNote.created_at.desc())
            .limit(40)
            .all()
        )
        owner_fn = ctx["owner_fn"]
        return [
            WorkspaceNoteOut(
                id=n.id,
                body_markdown=n.body_markdown,
                author_user_id=n.author_user_id,
                author_label=owner_fn(n.author_user_id),
                created_at=n.created_at,
            )
            for n in rows
        ]

    def _attachments(self, organization_id: int, ctx: dict) -> list[WorkspaceAttachmentOut]:
        entity_pairs: list[tuple[str, int]] = []
        if ctx.get("lead_id"):
            entity_pairs.append(("lead", ctx["lead_id"]))
        if ctx.get("company_id"):
            entity_pairs.append(("company", ctx["company_id"]))
        if ctx.get("person_id"):
            entity_pairs.append(("person", ctx["person_id"]))
        for oid in ctx.get("opportunity_ids") or []:
            entity_pairs.append(("opportunity", oid))
        if not entity_pairs:
            return []
        from sqlalchemy import or_, and_

        q = soft_alive(self.db.query(SalesAttachment), SalesAttachment).filter(
            SalesAttachment.organization_id == organization_id
        )
        q = q.filter(
            or_(
                *[
                    and_(
                        SalesAttachment.entity_type == et,
                        SalesAttachment.entity_id == eid,
                    )
                    for et, eid in entity_pairs
                ]
            )
        )
        rows = q.order_by(SalesAttachment.created_at.desc()).limit(40).all()
        vault_ids = [r.vault_document_id for r in rows]
        vaults = {
            v.id: v
            for v in self.db.query(VaultDocument)
            .filter(
                VaultDocument.organization_id == organization_id,
                VaultDocument.id.in_(vault_ids or [-1]),
            )
            .all()
        }
        out: list[WorkspaceAttachmentOut] = []
        for r in rows:
            v = vaults.get(r.vault_document_id)
            out.append(
                WorkspaceAttachmentOut(
                    id=r.id,
                    vault_document_id=r.vault_document_id,
                    label=r.label,
                    filename=v.original_filename if v else None,
                    preview_url=f"/vault?id={r.vault_document_id}",
                    open_url=f"/vault?id={r.vault_document_id}",
                )
            )
        return out

    def _timeline(
        self, organization_id: int, ctx: dict, now: datetime
    ) -> list[WorkspaceTimelineItemOut]:
        items: list[WorkspaceTimelineItemOut] = []

        def add(event_type: str, title: str, occurred_at: datetime | None, meta: dict | None = None, sid: str = ""):
            if not occurred_at:
                return
            items.append(
                WorkspaceTimelineItemOut(
                    id=sid or f"{event_type}-{occurred_at.isoformat()}",
                    event_type=event_type,
                    title=title,
                    occurred_at=occurred_at,
                    meta=meta or {},
                )
            )

        if ctx.get("lead_id"):
            lead = (
                soft_alive(self.db.query(SalesLead), SalesLead)
                .filter(SalesLead.id == ctx["lead_id"], SalesLead.organization_id == organization_id)
                .first()
            )
            if lead:
                add("lead_created", f"Lead créé — {lead.title}", lead.created_at, sid=f"lead-{lead.id}")

        if ctx.get("company_id"):
            company = (
                soft_alive(self.db.query(SalesCompany), SalesCompany)
                .filter(
                    SalesCompany.id == ctx["company_id"],
                    SalesCompany.organization_id == organization_id,
                )
                .first()
            )
            if company:
                add(
                    "company_created",
                    f"Entreprise créée — {company.name}",
                    company.created_at,
                    sid=f"company-{company.id}",
                )

        for oid in ctx.get("opportunity_ids") or []:
            opp = (
                soft_alive(self.db.query(SalesOpportunity), SalesOpportunity)
                .filter(SalesOpportunity.id == oid, SalesOpportunity.organization_id == organization_id)
                .first()
            )
            if opp:
                add(
                    "opportunity_created",
                    f"Opportunité créée — {opp.name}",
                    opp.created_at,
                    sid=f"opp-{opp.id}",
                )
                if opp.stage_entered_at and opp.stage_entered_at != opp.created_at:
                    add(
                        "stage_changed",
                        "Changement d'étape",
                        opp.stage_entered_at,
                        {"opportunity_id": str(opp.id)},
                        sid=f"stage-{opp.id}-{int(opp.stage_entered_at.timestamp())}",
                    )

        for a in self._activities(organization_id, ctx):
            add(
                "activity",
                f"{a.activity_type}: {a.subject}",
                a.activity_at,
                {"result": a.result or ""},
                sid=f"act-{a.id}",
            )
        for t in self._tasks(organization_id, ctx, now):
            add("task", f"Tâche — {t.title}", t.due_at or now, {"status": t.status}, sid=f"task-{t.id}")
        for n in self._notes(organization_id, ctx):
            add("note", "Note ajoutée", n.created_at, sid=f"note-{n.id}")
        for d in self._attachments(organization_id, ctx):
            # use attachment id; created_at not on out — approximate via now skip; reload
            att = (
                soft_alive(self.db.query(SalesAttachment), SalesAttachment)
                .filter(SalesAttachment.id == d.id)
                .first()
            )
            add(
                "document",
                f"Document — {d.filename or d.label or d.vault_document_id}",
                att.created_at if att else now,
                {"vault_document_id": str(d.vault_document_id)},
                sid=f"doc-{d.id}",
            )

        items.sort(key=lambda x: x.occurred_at, reverse=True)
        return items[:80]

    def _health_bundle(
        self,
        ctx: dict,
        activities: list[WorkspaceActivityOut],
        tasks: list[WorkspaceTaskOut],
        now: datetime,
    ) -> tuple[int, str, str, str, str]:
        last = activities[0].activity_at if activities else None
        next_act = next((a.activity_at for a in activities if a.activity_at > now), None)
        has_task = any(t.bucket in ("overdue", "today", "upcoming") and t.status in ACTIVE_TASK for t in tasks)
        if ctx.get("opp_row"):
            opp: SalesOpportunity = ctx["opp_row"]
            days = days_in_stage(ctx.get("stage_entered_at") or opp.created_at, now)
            score, label = health_score_for(
                days=days,
                has_contact=bool(ctx.get("person_id")),
                has_company=bool(ctx.get("company_id")),
                last_activity_at=last,
                next_activity_at=next_act,
                has_open_task=has_task,
                probability=int(ctx.get("probability") or 0),
                stage_probability=int(ctx.get("stage_probability") or 0),
                now=now,
            )
            risk, risk_label = risk_level_for(
                days=days,
                last_activity_at=last,
                expected_close=ctx.get("expected_close_date"),
                probability=int(ctx.get("probability") or 0),
                health=score,
                now=now,
            )
            expl = f"Score opportunité basé sur aging ({days} j.), activité et tâches."
            return score, label, expl, risk, risk_label

        # Non-opportunity entities: lighter health from activity/completeness
        days = 0
        if last:
            days = (now - last).days
        score, label = health_score_for(
            days=min(days, 60),
            has_contact=bool(ctx.get("person_id") or ctx.get("email")),
            has_company=bool(ctx.get("company_id")),
            last_activity_at=last,
            next_activity_at=next_act,
            has_open_task=has_task,
            probability=50,
            stage_probability=50,
            now=now,
        )
        risk, risk_label = risk_level_for(
            days=days,
            last_activity_at=last,
            expected_close=None,
            probability=50,
            health=score,
            now=now,
        )
        expl = "Health dérivé de l'activité relationnelle et de la complétude."
        return score, label, expl, risk, risk_label

    def _quick_actions(
        self, entity: str, entity_id: int, ctx: dict
    ) -> list[WorkspaceQuickActionOut]:
        actions = [
            WorkspaceQuickActionOut(
                id="activity", label="Nouvelle activité", href="/sales/activities"
            ),
            WorkspaceQuickActionOut(id="task", label="Nouvelle tâche", href="/sales/tasks"),
            WorkspaceQuickActionOut(
                id="note",
                label="Nouvelle note",
                href=f"/sales/workspace/{entity}/{entity_id}?tab=notes",
            ),
            WorkspaceQuickActionOut(
                id="opportunity", label="Nouvelle opportunité", href="/sales/pipeline"
            ),
        ]
        if entity == "opportunity" or (ctx.get("opportunity_ids") and len(ctx["opportunity_ids"]) == 1):
            oid = entity_id if entity == "opportunity" else ctx["opportunity_ids"][0]
            actions.append(
                WorkspaceQuickActionOut(
                    id="stage",
                    label="Changer étape",
                    href=f"/sales/pipeline?id={oid}",
                )
            )
        return actions
