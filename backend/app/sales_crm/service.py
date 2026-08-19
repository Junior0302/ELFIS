"""SalesPilot CRM services — org-scoped CRUD, soft delete, events, defaults."""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.sales_crm.defaults import (
    DEFAULT_LOST_REASONS,
    DEFAULT_PIPELINE_CODE,
    DEFAULT_PIPELINE_NAME,
    DEFAULT_STAGES,
    DEFAULT_WIN_REASONS,
)
from app.sales_crm.models import (
    SalesActivity,
    SalesAttachment,
    SalesCompany,
    SalesLead,
    SalesLostReason,
    SalesNote,
    SalesOpportunity,
    SalesPerson,
    SalesPipeline,
    SalesPipelineStage,
    SalesTag,
    SalesTask,
    SalesWinReason,
)
from app.sales_crm.schemas import SalesPagination

M = TypeVar("M")


def _now() -> datetime:
    return datetime.utcnow()


def soft_alive(query, model):
    return query.filter(model.deleted_at.is_(None))


def paginate(query, *, page: int, page_size: int) -> tuple[list[Any], SalesPagination]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, SalesPagination(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, ceil(total / page_size)) if total else 0,
    )


def _publish(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    aggregate_type: str,
    aggregate_id: int | str,
    payload: dict[str, Any],
    actor_user_id: int | None,
    idempotency_key: str,
) -> None:
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload,
            metadata={
                "source": "sales_crm",
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
            },
            idempotency_key=idempotency_key,
        ),
        commit=False,
    )


def ensure_default_pipeline(db: Session, *, organization_id: int, user_id: int | None) -> SalesPipeline:
    existing = (
        soft_alive(db.query(SalesPipeline), SalesPipeline)
        .filter(
            SalesPipeline.organization_id == organization_id,
            SalesPipeline.code == DEFAULT_PIPELINE_CODE,
        )
        .first()
    )
    if existing:
        return existing

    pipeline = SalesPipeline(
        organization_id=organization_id,
        name=DEFAULT_PIPELINE_NAME,
        code=DEFAULT_PIPELINE_CODE,
        is_default=True,
        is_active=True,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(pipeline)
    db.flush()

    for code, name, position, probability, is_won, is_lost in DEFAULT_STAGES:
        db.add(
            SalesPipelineStage(
                organization_id=organization_id,
                pipeline_id=pipeline.id,
                code=code,
                name=name,
                position=position,
                probability=probability,
                is_won=is_won,
                is_lost=is_lost,
                created_by=user_id,
                updated_by=user_id,
            )
        )

    for code, label in DEFAULT_LOST_REASONS:
        if not (
            soft_alive(db.query(SalesLostReason), SalesLostReason)
            .filter(SalesLostReason.organization_id == organization_id, SalesLostReason.code == code)
            .first()
        ):
            db.add(
                SalesLostReason(
                    organization_id=organization_id,
                    code=code,
                    label=label,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )
    for code, label in DEFAULT_WIN_REASONS:
        if not (
            soft_alive(db.query(SalesWinReason), SalesWinReason)
            .filter(SalesWinReason.organization_id == organization_id, SalesWinReason.code == code)
            .first()
        ):
            db.add(
                SalesWinReason(
                    organization_id=organization_id,
                    code=code,
                    label=label,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )

    db.flush()
    db.refresh(pipeline)
    return pipeline


def get_org_row(db: Session, model: type[M], *, organization_id: int, row_id: int) -> M:
    row = (
        soft_alive(db.query(model), model)
        .filter(model.id == row_id, model.organization_id == organization_id)  # type: ignore[attr-defined]
        .first()
    )
    if not row:
        raise HTTPException(404, detail={"code": "not_found", "message": "Ressource introuvable"})
    return row


def soft_delete(row: Any, *, user_id: int | None) -> None:
    row.deleted_at = _now()
    if hasattr(row, "updated_by"):
        row.updated_by = user_id
    if hasattr(row, "updated_at"):
        row.updated_at = _now()


# ----- Companies -----


def create_company(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesCompany:
    row = SalesCompany(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    _publish(
        db,
        event_name=EventNames.SALES_COMPANY_CREATED,
        organization_id=organization_id,
        aggregate_type="sales_company",
        aggregate_id=row.id,
        payload={"company_id": row.id, "name": row.name},
        actor_user_id=user_id,
        idempotency_key=f"sales:company:created:{organization_id}:{row.id}",
    )
    return row


def list_companies(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    q: str | None = None,
    sort: str = "-updated_at",
) -> tuple[list[SalesCompany], SalesPagination]:
    query = soft_alive(db.query(SalesCompany), SalesCompany).filter(
        SalesCompany.organization_id == organization_id
    )
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                SalesCompany.name.ilike(like),
                SalesCompany.email.ilike(like),
                SalesCompany.city.ilike(like),
            )
        )
    query = _apply_sort(query, SalesCompany, sort)
    return paginate(query, page=page, page_size=page_size)


# ----- People -----


def create_person(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesPerson:
    if data.get("company_id"):
        get_org_row(db, SalesCompany, organization_id=organization_id, row_id=int(data["company_id"]))
    row = SalesPerson(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    _publish(
        db,
        event_name=EventNames.SALES_PERSON_CREATED,
        organization_id=organization_id,
        aggregate_type="sales_person",
        aggregate_id=row.id,
        payload={"person_id": row.id, "first_name": row.first_name, "last_name": row.last_name},
        actor_user_id=user_id,
        idempotency_key=f"sales:person:created:{organization_id}:{row.id}",
    )
    return row


def list_people(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    q: str | None = None,
    company_id: int | None = None,
    sort: str = "-updated_at",
) -> tuple[list[SalesPerson], SalesPagination]:
    query = soft_alive(db.query(SalesPerson), SalesPerson).filter(
        SalesPerson.organization_id == organization_id
    )
    if company_id:
        query = query.filter(SalesPerson.company_id == company_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                SalesPerson.first_name.ilike(like),
                SalesPerson.last_name.ilike(like),
                SalesPerson.email.ilike(like),
            )
        )
    query = _apply_sort(query, SalesPerson, sort)
    return paginate(query, page=page, page_size=page_size)


# ----- Leads -----


def create_lead(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesLead:
    row = SalesLead(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    _publish(
        db,
        event_name=EventNames.SALES_LEAD_CREATED,
        organization_id=organization_id,
        aggregate_type="sales_lead",
        aggregate_id=row.id,
        payload={"lead_id": row.id, "title": row.title, "status": row.status},
        actor_user_id=user_id,
        idempotency_key=f"sales:lead:created:{organization_id}:{row.id}",
    )
    return row


def list_leads(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    q: str | None = None,
    status: str | None = None,
    sort: str = "-updated_at",
) -> tuple[list[SalesLead], SalesPagination]:
    query = soft_alive(db.query(SalesLead), SalesLead).filter(SalesLead.organization_id == organization_id)
    if status:
        query = query.filter(SalesLead.status == status)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                SalesLead.title.ilike(like),
                SalesLead.company_name.ilike(like),
                SalesLead.email.ilike(like),
            )
        )
    query = _apply_sort(query, SalesLead, sort)
    return paginate(query, page=page, page_size=page_size)


# ----- Opportunities -----


def create_opportunity(
    db: Session, *, organization_id: int, user_id: int | None, data: dict
) -> SalesOpportunity:
    pipeline = ensure_default_pipeline(db, organization_id=organization_id, user_id=user_id)
    pipeline_id = data.pop("pipeline_id", None) or pipeline.id
    pipe = get_org_row(db, SalesPipeline, organization_id=organization_id, row_id=int(pipeline_id))
    stage_id = data.pop("stage_id", None)
    if stage_id is None:
        first = (
            soft_alive(db.query(SalesPipelineStage), SalesPipelineStage)
            .filter(
                SalesPipelineStage.pipeline_id == pipe.id,
                SalesPipelineStage.organization_id == organization_id,
                SalesPipelineStage.is_active.is_(True),
            )
            .order_by(SalesPipelineStage.position.asc())
            .first()
        )
        if not first:
            raise HTTPException(400, detail={"code": "no_stage", "message": "Pipeline sans étape"})
        stage = first
    else:
        stage = get_org_row(db, SalesPipelineStage, organization_id=organization_id, row_id=int(stage_id))
        if stage.pipeline_id != pipe.id:
            raise HTTPException(400, detail={"code": "stage_mismatch", "message": "Étape hors pipeline"})

    probability = data.pop("probability", None)
    if probability is None:
        probability = stage.probability

    row = SalesOpportunity(
        organization_id=organization_id,
        created_by=user_id,
        updated_by=user_id,
        pipeline_id=pipe.id,
        stage_id=stage.id,
        probability=int(probability),
        stage_entered_at=_now(),
        **data,
    )
    db.add(row)
    db.flush()
    _publish(
        db,
        event_name=EventNames.SALES_OPPORTUNITY_CREATED,
        organization_id=organization_id,
        aggregate_type="sales_opportunity",
        aggregate_id=row.id,
        payload={
            "opportunity_id": row.id,
            "name": row.name,
            "pipeline_id": row.pipeline_id,
            "stage_id": row.stage_id,
            "status": row.status,
        },
        actor_user_id=user_id,
        idempotency_key=f"sales:opportunity:created:{organization_id}:{row.id}",
    )
    return row


def update_opportunity(
    db: Session,
    *,
    organization_id: int,
    user_id: int | None,
    opportunity_id: int,
    data: dict,
) -> SalesOpportunity:
    row = get_org_row(db, SalesOpportunity, organization_id=organization_id, row_id=opportunity_id)
    old_stage = row.stage_id
    old_amount = row.estimated_amount
    old_probability = row.probability
    if "stage_id" in data and data["stage_id"] is not None:
        stage = get_org_row(
            db, SalesPipelineStage, organization_id=organization_id, row_id=int(data["stage_id"])
        )
        if stage.pipeline_id != (data.get("pipeline_id") or row.pipeline_id):
            raise HTTPException(400, detail={"code": "stage_mismatch", "message": "Étape hors pipeline"})
        if data.get("probability") is None:
            data["probability"] = stage.probability
        if stage.is_won:
            data.setdefault("status", "won")
        if stage.is_lost:
            data.setdefault("status", "lost")

    for key, value in data.items():
        if value is not None or key in data:
            setattr(row, key, value)
    row.updated_by = user_id
    row.updated_at = _now()
    if row.stage_id != old_stage:
        row.stage_entered_at = _now()
        # Leaving won/lost → reopen
        stage_now = get_org_row(
            db, SalesPipelineStage, organization_id=organization_id, row_id=row.stage_id
        )
        if not stage_now.is_won and not stage_now.is_lost and row.status in ("won", "lost"):
            row.status = "open"
    db.flush()

    if row.stage_id != old_stage:
        _publish(
            db,
            event_name=EventNames.SALES_OPPORTUNITY_STAGE_CHANGED,
            organization_id=organization_id,
            aggregate_type="sales_opportunity",
            aggregate_id=row.id,
            payload={
                "opportunity_id": row.id,
                "from_stage_id": old_stage,
                "to_stage_id": row.stage_id,
                "status": row.status,
            },
            actor_user_id=user_id,
            idempotency_key=f"sales:opportunity:stage:{organization_id}:{row.id}:{old_stage}:{row.stage_id}",
        )
    amount_changed = old_amount != row.estimated_amount
    probability_changed = old_probability != row.probability
    _publish(
        db,
        event_name=EventNames.SALES_OPPORTUNITY_UPDATED,
        organization_id=organization_id,
        aggregate_type="sales_opportunity",
        aggregate_id=row.id,
        payload={
            "opportunity_id": row.id,
            "stage_id": row.stage_id,
            "status": row.status,
            "probability": row.probability,
            "estimated_amount": str(row.estimated_amount) if row.estimated_amount is not None else None,
            "amount_changed": amount_changed,
            "probability_changed": probability_changed,
            "previous_amount": str(old_amount) if old_amount is not None else None,
            "previous_probability": old_probability,
        },
        actor_user_id=user_id,
        idempotency_key=f"sales:opportunity:updated:{organization_id}:{row.id}:{int(row.updated_at.timestamp()) if row.updated_at else 0}",
    )
    return row


def list_opportunities(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    q: str | None = None,
    status: str | None = None,
    pipeline_id: int | None = None,
    stage_id: int | None = None,
    sort: str = "-updated_at",
) -> tuple[list[SalesOpportunity], SalesPagination]:
    query = soft_alive(db.query(SalesOpportunity), SalesOpportunity).filter(
        SalesOpportunity.organization_id == organization_id
    )
    if status:
        query = query.filter(SalesOpportunity.status == status)
    if pipeline_id:
        query = query.filter(SalesOpportunity.pipeline_id == pipeline_id)
    if stage_id:
        query = query.filter(SalesOpportunity.stage_id == stage_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(SalesOpportunity.name.ilike(like))
    query = _apply_sort(query, SalesOpportunity, sort)
    return paginate(query, page=page, page_size=page_size)


# ----- Activities / Tasks / Notes / Tags / Attachments -----


def create_activity(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesActivity:
    if not data.get("activity_at"):
        data["activity_at"] = _now()
    if not data.get("owner_user_id"):
        data["owner_user_id"] = user_id
    row = SalesActivity(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    _publish(
        db,
        event_name=EventNames.SALES_ACTIVITY_CREATED,
        organization_id=organization_id,
        aggregate_type="sales_activity",
        aggregate_id=row.id,
        payload={
            "activity_id": row.id,
            "activity_type": row.activity_type,
            "subject": row.subject,
        },
        actor_user_id=user_id,
        idempotency_key=f"sales:activity:created:{organization_id}:{row.id}",
    )
    return row


def list_activities(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    q: str | None = None,
    activity_type: str | None = None,
    opportunity_id: int | None = None,
    sort: str = "-activity_at",
) -> tuple[list[SalesActivity], SalesPagination]:
    query = soft_alive(db.query(SalesActivity), SalesActivity).filter(
        SalesActivity.organization_id == organization_id
    )
    if activity_type:
        query = query.filter(SalesActivity.activity_type == activity_type)
    if opportunity_id:
        query = query.filter(SalesActivity.opportunity_id == opportunity_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(SalesActivity.subject.ilike(like), SalesActivity.comment.ilike(like)))
    query = _apply_sort(query, SalesActivity, sort, default_field="activity_at")
    return paginate(query, page=page, page_size=page_size)


def create_task(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesTask:
    row = SalesTask(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    _publish(
        db,
        event_name=EventNames.SALES_TASK_CREATED,
        organization_id=organization_id,
        aggregate_type="sales_task",
        aggregate_id=row.id,
        payload={"task_id": row.id, "title": row.title, "status": row.status},
        actor_user_id=user_id,
        idempotency_key=f"sales:task:created:{organization_id}:{row.id}",
    )
    return row


def update_task(
    db: Session, *, organization_id: int, user_id: int | None, task_id: int, data: dict
) -> SalesTask:
    row = get_org_row(db, SalesTask, organization_id=organization_id, row_id=task_id)
    prev_status = row.status
    for key, value in data.items():
        setattr(row, key, value)
    if data.get("status") == "done" and prev_status != "done":
        row.completed_at = _now()
        _publish(
            db,
            event_name=EventNames.SALES_TASK_COMPLETED,
            organization_id=organization_id,
            aggregate_type="sales_task",
            aggregate_id=row.id,
            payload={"task_id": row.id, "title": row.title, "status": row.status},
            actor_user_id=user_id,
            idempotency_key=f"sales:task:completed:{organization_id}:{row.id}",
        )
    row.updated_by = user_id
    row.updated_at = _now()
    db.flush()
    return row


def list_tasks(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    q: str | None = None,
    status: str | None = None,
    opportunity_id: int | None = None,
    sort: str = "-updated_at",
) -> tuple[list[SalesTask], SalesPagination]:
    query = soft_alive(db.query(SalesTask), SalesTask).filter(SalesTask.organization_id == organization_id)
    if status:
        query = query.filter(SalesTask.status == status)
    if opportunity_id:
        query = query.filter(SalesTask.opportunity_id == opportunity_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(SalesTask.title.ilike(like), SalesTask.description.ilike(like)))
    query = _apply_sort(query, SalesTask, sort)
    return paginate(query, page=page, page_size=page_size)


def create_note(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesNote:
    row = SalesNote(
        organization_id=organization_id,
        created_by=user_id,
        updated_by=user_id,
        author_user_id=user_id,
        **data,
    )
    db.add(row)
    db.flush()
    return row


def list_notes(
    db: Session,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> tuple[list[SalesNote], SalesPagination]:
    query = soft_alive(db.query(SalesNote), SalesNote).filter(SalesNote.organization_id == organization_id)
    if entity_type:
        query = query.filter(SalesNote.entity_type == entity_type)
    if entity_id:
        query = query.filter(SalesNote.entity_id == entity_id)
    query = query.order_by(SalesNote.created_at.desc())
    return paginate(query, page=page, page_size=page_size)


def create_tag(db: Session, *, organization_id: int, user_id: int | None, data: dict) -> SalesTag:
    row = SalesTag(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    return row


def list_tags(db: Session, *, organization_id: int) -> list[SalesTag]:
    return (
        soft_alive(db.query(SalesTag), SalesTag)
        .filter(SalesTag.organization_id == organization_id)
        .order_by(SalesTag.name.asc())
        .all()
    )


def create_attachment(
    db: Session, *, organization_id: int, user_id: int | None, data: dict
) -> SalesAttachment:
    # Vault document must belong to org — light check if model available
    from app.models_vault import VaultDocument

    vault = (
        db.query(VaultDocument)
        .filter(
            VaultDocument.id == int(data["vault_document_id"]),
            VaultDocument.organization_id == organization_id,
        )
        .first()
    )
    if not vault:
        raise HTTPException(404, detail={"code": "vault_not_found", "message": "Document Vault introuvable"})
    row = SalesAttachment(organization_id=organization_id, created_by=user_id, updated_by=user_id, **data)
    db.add(row)
    db.flush()
    return row


def _apply_sort(query, model, sort: str, default_field: str = "updated_at"):
    desc = sort.startswith("-")
    field_name = sort[1:] if desc else sort
    col = getattr(model, field_name, None) or getattr(model, default_field)
    return query.order_by(col.desc() if desc else col.asc())
