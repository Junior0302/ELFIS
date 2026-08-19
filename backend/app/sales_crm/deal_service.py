"""DealWorkspaceService — opportunity cockpit aggregation (S1.5).

Backend is the single source of truth. Forecast = amount × probability / 100.
Reuses Health (S1.3) and Relationship Score (S1.4). No AI / quote engine.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_models import ElfisEvent
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_saas import User
from app.models_vault import VaultDocument
from app.sales_crm.deal_schemas import (
    DealActivityOut,
    DealAttachmentOut,
    DealForecastOut,
    DealHeaderOut,
    DealHealthOut,
    DealNoteOut,
    DealParticipantOut,
    DealProductOut,
    DealQuickActionOut,
    DealRelationshipOut,
    DealSummaryOut,
    DealTaskOut,
    DealTimelineItemOut,
    DealWorkspaceOut,
)
from app.sales_crm.models import (
    PARTICIPANT_ROLES,
    SalesActivity,
    SalesAttachment,
    SalesCompany,
    SalesNote,
    SalesOpportunity,
    SalesOpportunityParticipant,
    SalesOpportunityProduct,
    SalesPerson,
    SalesPipeline,
    SalesPipelineStage,
    SalesTask,
)
from app.sales_crm.pipeline_service import days_in_stage, health_score_for, risk_level_for
from app.sales_crm.service import get_org_row, soft_alive, soft_delete
from app.sales_crm.workspace_service import relationship_score_for

ACTIVE_TASK = ("todo", "in_progress")
ACTIVITY_TYPES = ("call", "email", "meeting", "visit", "task", "note")

ROLE_LABELS = {
    "decision_maker": "Décideur",
    "influencer": "Influenceur",
    "technical": "Technique",
    "buyer": "Acheteur",
    "primary": "Contact principal",
}

TWO = Decimal("0.01")


def _now() -> datetime:
    return datetime.utcnow()


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    return datetime.combine(d, time.min), datetime.combine(d, time.max)


def compute_line_total(
    quantity: Decimal, unit_price: Decimal, discount_percent: Decimal
) -> Decimal:
    """Server-side line total — no frontend calculation."""
    qty = Decimal(quantity or 0)
    price = Decimal(unit_price or 0)
    disc = Decimal(discount_percent or 0)
    if disc < 0:
        disc = Decimal("0")
    if disc > 100:
        disc = Decimal("100")
    subtotal = qty * price
    total = subtotal * (Decimal("100") - disc) / Decimal("100")
    return total.quantize(TWO, rounding=ROUND_HALF_UP)


def compute_forecast(amount: Decimal | None, probability: int) -> Decimal:
    base = Decimal(amount or 0)
    prob = max(0, min(100, int(probability or 0)))
    return (base * Decimal(prob) / Decimal("100")).quantize(TWO, rounding=ROUND_HALF_UP)


def _owner_label(db: Session, uid: int | None, cache: dict[int, str]) -> str | None:
    if not uid:
        return None
    if uid in cache:
        return cache[uid]
    u = db.get(User, uid)
    if not u:
        return None
    label = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
    cache[uid] = label
    return label


class DealWorkspaceService:
    def __init__(self, db: Session):
        self.db = db

    def build(
        self,
        *,
        organization_id: int,
        opportunity_id: int,
        user_id: int | None = None,
        publish_opened: bool = True,
    ) -> DealWorkspaceOut:
        opp = get_org_row(
            self.db, SalesOpportunity, organization_id=organization_id, row_id=opportunity_id
        )
        now = _now()
        owners: dict[int, str] = {}

        company = None
        if opp.company_id:
            company = (
                soft_alive(self.db.query(SalesCompany), SalesCompany)
                .filter(
                    SalesCompany.id == opp.company_id,
                    SalesCompany.organization_id == organization_id,
                )
                .first()
            )
        stage = (
            soft_alive(self.db.query(SalesPipelineStage), SalesPipelineStage)
            .filter(SalesPipelineStage.id == opp.stage_id)
            .first()
        )
        pipe = (
            soft_alive(self.db.query(SalesPipeline), SalesPipeline)
            .filter(SalesPipeline.id == opp.pipeline_id)
            .first()
        )

        products = self._products(organization_id, opportunity_id)
        participants = self._participants(organization_id, opp)
        activities = self._activities(organization_id, opp)
        tasks = self._tasks(organization_id, opp, now)
        notes = self._notes(organization_id, opportunity_id)
        attachments = self._attachments(organization_id, opportunity_id)
        timeline = self._timeline(organization_id, opp, company, now)

        last_activity_at = activities[0].activity_at if activities else None
        days = days_in_stage(opp.stage_entered_at or opp.created_at, now)
        has_open_task = any(t.status in ACTIVE_TASK for t in tasks)
        health, health_label = health_score_for(
            days=days,
            has_contact=bool(opp.person_id or participants),
            has_company=bool(opp.company_id),
            last_activity_at=last_activity_at,
            next_activity_at=None,
            has_open_task=has_open_task,
            probability=opp.probability,
            stage_probability=stage.probability if stage else opp.probability,
            now=now,
        )
        risk, risk_label = risk_level_for(
            days=days,
            last_activity_at=last_activity_at,
            expected_close=opp.expected_close_date,
            probability=opp.probability,
            health=health,
            now=now,
        )
        health_expl = "Health dérivé de l'étape, de l'activité et de la complétude du deal."

        has_email = any(p.email for p in participants)
        has_phone = any(p.phone for p in participants)
        rel_score, rel_label, rel_expl, rel_factors = relationship_score_for(
            activities_count=len(activities),
            last_activity_at=last_activity_at,
            contacts_count=len(participants),
            has_email=has_email,
            has_phone=has_phone,
            has_company=bool(opp.company_id),
            created_at=opp.created_at,
            now=now,
        )

        forecast_amount = compute_forecast(opp.estimated_amount, opp.probability)
        products_total = sum((p.line_total for p in products), Decimal("0"))
        open_tasks = sum(1 for t in tasks if t.bucket in ("overdue", "today", "upcoming") and t.status in ACTIVE_TASK)

        header = DealHeaderOut(
            opportunity_id=opp.id,
            name=opp.name,
            company_id=opp.company_id,
            company_name=company.name if company else None,
            amount=opp.estimated_amount,
            pipeline_id=opp.pipeline_id,
            pipeline_name=pipe.name if pipe else None,
            stage_id=opp.stage_id,
            stage_name=stage.name if stage else None,
            owner_label=_owner_label(self.db, opp.owner_user_id, owners),
            probability=opp.probability,
            status=opp.status,
            health_score=health,
            health_label=health_label,
            health_explanation=health_expl,
            relationship_score=rel_score,
            relationship_label=rel_label,
            risk_level=risk,
            risk_label=risk_label,
            forecast_amount=forecast_amount,
            last_activity_at=last_activity_at,
            expected_close_date=opp.expected_close_date,
            created_at=opp.created_at,
        )

        summary = DealSummaryOut(
            participants_count=len(participants),
            products_count=len(products),
            products_total=products_total if isinstance(products_total, Decimal) else Decimal(str(products_total)),
            activities_count=len(activities),
            open_tasks_count=open_tasks,
            notes_count=len(notes),
            documents_count=len(attachments),
            forecast_amount=forecast_amount,
        )

        forecast = DealForecastOut(
            amount=opp.estimated_amount or Decimal("0"),
            probability=opp.probability,
            weighted_amount=forecast_amount,
        )

        out = DealWorkspaceOut(
            header=header,
            summary=summary,
            participants=participants,
            products=products,
            activities=activities,
            tasks=tasks,
            notes=notes,
            attachments=attachments,
            timeline=timeline,
            health=DealHealthOut(
                score=health,
                label=health_label,
                explanation=health_expl,
                risk_level=risk,
                risk_label=risk_label,
            ),
            relationship=DealRelationshipOut(
                score=rel_score,
                label=rel_label,
                explanation=rel_expl,
                factors=rel_factors,
            ),
            forecast=forecast,
            quick_actions=self._quick_actions(opp),
            generated_at=now,
        )

        if publish_opened:
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.SALES_DEAL_OPENED,
                    organization_id=organization_id,
                    aggregate_type="sales_opportunity",
                    aggregate_id=str(opp.id),
                    payload={"opportunity_id": opp.id},
                    metadata={
                        "source": "sales_crm",
                        "actor_user_id": str(user_id) if user_id else None,
                    },
                    idempotency_key=f"sales:deal:opened:{organization_id}:{opp.id}:{int(now.timestamp())}",
                ),
                commit=False,
            )
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.SALES_FORECAST_UPDATED,
                    organization_id=organization_id,
                    aggregate_type="sales_opportunity",
                    aggregate_id=str(opp.id),
                    payload={
                        "opportunity_id": opp.id,
                        "forecast_amount": str(forecast_amount),
                        "probability": opp.probability,
                        "amount": str(opp.estimated_amount or 0),
                    },
                    metadata={"source": "sales_crm"},
                    idempotency_key=f"sales:forecast:updated:{organization_id}:{opp.id}:{forecast_amount}:{opp.probability}",
                ),
                commit=False,
            )

        return out

    def _products(self, organization_id: int, opportunity_id: int) -> list[DealProductOut]:
        rows = (
            soft_alive(self.db.query(SalesOpportunityProduct), SalesOpportunityProduct)
            .filter(
                SalesOpportunityProduct.organization_id == organization_id,
                SalesOpportunityProduct.opportunity_id == opportunity_id,
            )
            .order_by(SalesOpportunityProduct.position.asc(), SalesOpportunityProduct.id.asc())
            .all()
        )
        return [
            DealProductOut(
                id=r.id,
                name=r.name,
                description=r.description,
                quantity=r.quantity,
                unit_price=r.unit_price,
                discount_percent=r.discount_percent,
                line_total=r.line_total,
                position=r.position,
            )
            for r in rows
        ]

    def _participants(
        self, organization_id: int, opp: SalesOpportunity
    ) -> list[DealParticipantOut]:
        rows = (
            soft_alive(self.db.query(SalesOpportunityParticipant), SalesOpportunityParticipant)
            .filter(
                SalesOpportunityParticipant.organization_id == organization_id,
                SalesOpportunityParticipant.opportunity_id == opp.id,
            )
            .all()
        )
        person_ids = {r.person_id for r in rows}
        if opp.person_id:
            person_ids.add(opp.person_id)
        people = {
            p.id: p
            for p in soft_alive(self.db.query(SalesPerson), SalesPerson)
            .filter(
                SalesPerson.organization_id == organization_id,
                SalesPerson.id.in_(person_ids or [-1]),
            )
            .all()
        }

        out: list[DealParticipantOut] = []
        seen_keys: set[tuple[int, str]] = set()

        for r in rows:
            p = people.get(r.person_id)
            if not p:
                continue
            role = r.role if r.role in PARTICIPANT_ROLES else "primary"
            seen_keys.add((p.id, role))
            out.append(
                DealParticipantOut(
                    id=r.id,
                    person_id=p.id,
                    first_name=p.first_name,
                    last_name=p.last_name,
                    email=p.email,
                    phone=p.phone,
                    job_title=p.job_title,
                    role=role,  # type: ignore[arg-type]
                    role_label=ROLE_LABELS.get(role, role),
                    is_primary=bool(r.is_primary or role == "primary"),
                    href=f"/sales/workspace/person/{p.id}",
                )
            )

        # Ensure opportunity.person_id appears as primary if missing
        if opp.person_id and opp.person_id in people and (opp.person_id, "primary") not in seen_keys:
            p = people[opp.person_id]
            out.insert(
                0,
                DealParticipantOut(
                    id=None,
                    person_id=p.id,
                    first_name=p.first_name,
                    last_name=p.last_name,
                    email=p.email,
                    phone=p.phone,
                    job_title=p.job_title,
                    role="primary",
                    role_label=ROLE_LABELS["primary"],
                    is_primary=True,
                    href=f"/sales/workspace/person/{p.id}",
                ),
            )

        role_order = {r: i for i, r in enumerate(PARTICIPANT_ROLES)}
        out.sort(key=lambda x: (0 if x.is_primary else 1, role_order.get(x.role, 99), x.last_name))
        return out

    def _activities(
        self, organization_id: int, opp: SalesOpportunity
    ) -> list[DealActivityOut]:
        owners: dict[int, str] = {}
        q = soft_alive(self.db.query(SalesActivity), SalesActivity).filter(
            SalesActivity.organization_id == organization_id,
            SalesActivity.activity_type.in_(ACTIVITY_TYPES),
        )
        clauses = [SalesActivity.opportunity_id == opp.id]
        if opp.company_id:
            clauses.append(SalesActivity.company_id == opp.company_id)
        if opp.person_id:
            clauses.append(SalesActivity.person_id == opp.person_id)
        rows = (
            q.filter(or_(*clauses))
            .order_by(SalesActivity.activity_at.desc())
            .limit(40)
            .all()
        )
        return [
            DealActivityOut(
                id=a.id,
                activity_type=a.activity_type,
                subject=a.subject,
                activity_at=a.activity_at,
                result=a.result,
                owner_label=_owner_label(self.db, a.owner_user_id, owners),
            )
            for a in rows
        ]

    def _tasks(
        self, organization_id: int, opp: SalesOpportunity, now: datetime
    ) -> list[DealTaskOut]:
        q = soft_alive(self.db.query(SalesTask), SalesTask).filter(
            SalesTask.organization_id == organization_id
        )
        clauses = [SalesTask.opportunity_id == opp.id]
        if opp.company_id:
            clauses.append(SalesTask.company_id == opp.company_id)
        if opp.person_id:
            clauses.append(SalesTask.person_id == opp.person_id)
        rows = q.filter(or_(*clauses)).order_by(SalesTask.due_at.asc()).limit(40).all()
        today = now.date()
        today_start, today_end = _day_bounds(today)
        out: list[DealTaskOut] = []
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
                DealTaskOut(
                    id=t.id,
                    title=t.title,
                    status=t.status,
                    priority=t.priority,
                    due_at=t.due_at,
                    bucket=bucket,
                )
            )
        order = {"overdue": 0, "today": 1, "upcoming": 2, "other": 3}
        out.sort(key=lambda x: order.get(x.bucket, 9))
        return out

    def _notes(self, organization_id: int, opportunity_id: int) -> list[DealNoteOut]:
        owners: dict[int, str] = {}
        rows = (
            soft_alive(self.db.query(SalesNote), SalesNote)
            .filter(
                SalesNote.organization_id == organization_id,
                SalesNote.entity_type == "opportunity",
                SalesNote.entity_id == opportunity_id,
            )
            .order_by(SalesNote.created_at.desc())
            .limit(40)
            .all()
        )
        return [
            DealNoteOut(
                id=n.id,
                body_markdown=n.body_markdown,
                author_user_id=n.author_user_id,
                author_label=_owner_label(self.db, n.author_user_id, owners),
                created_at=n.created_at,
            )
            for n in rows
        ]

    def _attachments(
        self, organization_id: int, opportunity_id: int
    ) -> list[DealAttachmentOut]:
        rows = (
            soft_alive(self.db.query(SalesAttachment), SalesAttachment)
            .filter(
                SalesAttachment.organization_id == organization_id,
                SalesAttachment.entity_type == "opportunity",
                SalesAttachment.entity_id == opportunity_id,
            )
            .order_by(SalesAttachment.created_at.desc())
            .limit(40)
            .all()
        )
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
        out: list[DealAttachmentOut] = []
        for r in rows:
            v = vaults.get(r.vault_document_id)
            out.append(
                DealAttachmentOut(
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
        self,
        organization_id: int,
        opp: SalesOpportunity,
        company: SalesCompany | None,
        now: datetime,
    ) -> list[DealTimelineItemOut]:
        items: list[DealTimelineItemOut] = []

        def add(
            event_type: str,
            title: str,
            occurred_at: datetime | None,
            meta: dict | None = None,
            sid: str = "",
        ):
            if not occurred_at:
                return
            items.append(
                DealTimelineItemOut(
                    id=sid or f"{event_type}-{occurred_at.isoformat()}",
                    event_type=event_type,
                    title=title,
                    occurred_at=occurred_at,
                    meta={k: str(v) for k, v in (meta or {}).items()},
                )
            )

        add("opportunity_created", f"Opportunité créée — {opp.name}", opp.created_at, sid=f"opp-{opp.id}")
        if company:
            add(
                "company_created",
                f"Entreprise — {company.name}",
                company.created_at,
                sid=f"company-{company.id}",
            )
        if opp.stage_entered_at and opp.stage_entered_at != opp.created_at:
            add(
                "stage_changed",
                "Étape modifiée",
                opp.stage_entered_at,
                {"opportunity_id": str(opp.id)},
                sid=f"stage-{opp.id}-{int(opp.stage_entered_at.timestamp())}",
            )

        # Products currently on the deal (always visible even if event bus empty)
        for prod in (
            soft_alive(self.db.query(SalesOpportunityProduct), SalesOpportunityProduct)
            .filter(
                SalesOpportunityProduct.organization_id == organization_id,
                SalesOpportunityProduct.opportunity_id == opp.id,
            )
            .all()
        ):
            add(
                "product_added",
                f"Produit ajouté — {prod.name}",
                prod.created_at,
                {"product_id": str(prod.id)},
                sid=f"prod-{prod.id}",
            )

        # Domain events: amount / probability / stage / products
        event_names = (
            EventNames.SALES_OPPORTUNITY_UPDATED,
            EventNames.SALES_OPPORTUNITY_STAGE_CHANGED,
            EventNames.SALES_PRODUCT_ADDED,
            EventNames.SALES_PRODUCT_REMOVED,
        )
        events = (
            self.db.query(ElfisEvent)
            .filter(
                ElfisEvent.organization_id == organization_id,
                ElfisEvent.aggregate_type == "sales_opportunity",
                ElfisEvent.aggregate_id == str(opp.id),
                ElfisEvent.event_name.in_(event_names),
            )
            .order_by(ElfisEvent.created_at.desc())
            .limit(60)
            .all()
        )
        for ev in events:
            payload = ev.payload or {}
            if ev.event_name == EventNames.SALES_OPPORTUNITY_STAGE_CHANGED:
                add(
                    "stage_changed",
                    "Étape modifiée",
                    ev.created_at,
                    payload,
                    sid=f"ev-stage-{ev.event_id}",
                )
            elif ev.event_name == EventNames.SALES_PRODUCT_ADDED:
                add(
                    "product_added",
                    f"Produit ajouté — {payload.get('name', '')}",
                    ev.created_at,
                    payload,
                    sid=f"ev-prod-add-{ev.event_id}",
                )
            elif ev.event_name == EventNames.SALES_PRODUCT_REMOVED:
                add(
                    "product_removed",
                    f"Produit supprimé — {payload.get('name', '')}",
                    ev.created_at,
                    payload,
                    sid=f"ev-prod-rm-{ev.event_id}",
                )
            elif ev.event_name == EventNames.SALES_OPPORTUNITY_UPDATED:
                if payload.get("amount_changed"):
                    add(
                        "amount_changed",
                        f"Montant modifié — {payload.get('estimated_amount', '')}",
                        ev.created_at,
                        payload,
                        sid=f"ev-amt-{ev.event_id}",
                    )
                if payload.get("probability_changed"):
                    add(
                        "probability_changed",
                        f"Probabilité modifiée — {payload.get('probability', '')} %",
                        ev.created_at,
                        payload,
                        sid=f"ev-prob-{ev.event_id}",
                    )

        for a in self._activities(organization_id, opp):
            add(
                "activity",
                f"{a.activity_type}: {a.subject}",
                a.activity_at,
                {"result": a.result or ""},
                sid=f"act-{a.id}",
            )
        for t in self._tasks(organization_id, opp, now):
            add("task", f"Tâche — {t.title}", t.due_at or now, {"status": t.status}, sid=f"task-{t.id}")
        for n in self._notes(organization_id, opp.id):
            add("note", "Note ajoutée", n.created_at, sid=f"note-{n.id}")
        for d in self._attachments(organization_id, opp.id):
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

        # Deduplicate by id, keep newest first
        seen: set[str] = set()
        unique: list[DealTimelineItemOut] = []
        items.sort(key=lambda x: x.occurred_at, reverse=True)
        for it in items:
            if it.id in seen:
                continue
            seen.add(it.id)
            unique.append(it)
        return unique[:80]

    def _quick_actions(self, opp: SalesOpportunity) -> list[DealQuickActionOut]:
        base = f"/sales/deals/{opp.id}"
        actions = [
            DealQuickActionOut(id="activity", label="Nouvelle activité", href="/sales/activities"),
            DealQuickActionOut(id="task", label="Nouvelle tâche", href="/sales/tasks"),
            DealQuickActionOut(id="note", label="Nouvelle note", href=f"{base}?tab=notes"),
            DealQuickActionOut(
                id="stage", label="Changer étape", href=f"/sales/pipeline?id={opp.id}"
            ),
            DealQuickActionOut(id="product", label="Ajouter produit", href=f"{base}?tab=products"),
            DealQuickActionOut(
                id="quote",
                label="Préparer devis",
                href=f"/sales/proposals/new?opportunity_id={opp.id}",
            ),
        ]
        return actions


# ----- Product / participant mutations -----


def add_product(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    opportunity_id: int,
    data: dict,
) -> SalesOpportunityProduct:
    get_org_row(db, SalesOpportunity, organization_id=organization_id, row_id=opportunity_id)
    qty = Decimal(str(data.get("quantity", 1)))
    price = Decimal(str(data.get("unit_price", 0)))
    disc = Decimal(str(data.get("discount_percent", 0)))
    total = compute_line_total(qty, price, disc)
    row = SalesOpportunityProduct(
        organization_id=organization_id,
        created_by=user_id,
        updated_by=user_id,
        opportunity_id=opportunity_id,
        name=data["name"],
        description=data.get("description"),
        quantity=qty,
        unit_price=price,
        discount_percent=disc,
        line_total=total,
        position=int(data.get("position") or 0),
    )
    db.add(row)
    db.flush()
    safe_publish(
        db,
        DomainEvent(
            event_name=EventNames.SALES_PRODUCT_ADDED,
            organization_id=organization_id,
            aggregate_type="sales_opportunity",
            aggregate_id=str(opportunity_id),
            payload={
                "opportunity_id": opportunity_id,
                "product_id": row.id,
                "name": row.name,
                "line_total": str(row.line_total),
            },
            metadata={"source": "sales_crm", "actor_user_id": str(user_id) if user_id else None},
            idempotency_key=f"sales:product:added:{organization_id}:{opportunity_id}:{row.id}",
        ),
        commit=False,
    )
    return row


def update_product(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    opportunity_id: int,
    product_id: int,
    data: dict,
) -> SalesOpportunityProduct:
    row = (
        soft_alive(db.query(SalesOpportunityProduct), SalesOpportunityProduct)
        .filter(
            SalesOpportunityProduct.organization_id == organization_id,
            SalesOpportunityProduct.opportunity_id == opportunity_id,
            SalesOpportunityProduct.id == product_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail={"code": "not_found", "message": "Produit introuvable"})
    for key in ("name", "description", "position"):
        if key in data and data[key] is not None:
            setattr(row, key, data[key])
    if "quantity" in data and data["quantity"] is not None:
        row.quantity = Decimal(str(data["quantity"]))
    if "unit_price" in data and data["unit_price"] is not None:
        row.unit_price = Decimal(str(data["unit_price"]))
    if "discount_percent" in data and data["discount_percent"] is not None:
        row.discount_percent = Decimal(str(data["discount_percent"]))
    row.line_total = compute_line_total(row.quantity, row.unit_price, row.discount_percent)
    row.updated_by = user_id
    row.updated_at = _now()
    db.flush()
    return row


def remove_product(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    opportunity_id: int,
    product_id: int,
) -> None:
    row = (
        soft_alive(db.query(SalesOpportunityProduct), SalesOpportunityProduct)
        .filter(
            SalesOpportunityProduct.organization_id == organization_id,
            SalesOpportunityProduct.opportunity_id == opportunity_id,
            SalesOpportunityProduct.id == product_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail={"code": "not_found", "message": "Produit introuvable"})
    name = row.name
    soft_delete(row, user_id=user_id)
    safe_publish(
        db,
        DomainEvent(
            event_name=EventNames.SALES_PRODUCT_REMOVED,
            organization_id=organization_id,
            aggregate_type="sales_opportunity",
            aggregate_id=str(opportunity_id),
            payload={
                "opportunity_id": opportunity_id,
                "product_id": product_id,
                "name": name,
            },
            metadata={"source": "sales_crm", "actor_user_id": str(user_id) if user_id else None},
            idempotency_key=f"sales:product:removed:{organization_id}:{opportunity_id}:{product_id}",
        ),
        commit=False,
    )


def add_participant(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    opportunity_id: int,
    data: dict,
) -> SalesOpportunityParticipant:
    get_org_row(db, SalesOpportunity, organization_id=organization_id, row_id=opportunity_id)
    person_id = int(data["person_id"])
    get_org_row(db, SalesPerson, organization_id=organization_id, row_id=person_id)
    role = data.get("role") or "primary"
    if role not in PARTICIPANT_ROLES:
        raise HTTPException(400, detail={"code": "invalid_role", "message": "Rôle participant invalide"})
    row = SalesOpportunityParticipant(
        organization_id=organization_id,
        created_by=user_id,
        updated_by=user_id,
        opportunity_id=opportunity_id,
        person_id=person_id,
        role=role,
        is_primary=bool(data.get("is_primary") or role == "primary"),
    )
    db.add(row)
    db.flush()
    return row
