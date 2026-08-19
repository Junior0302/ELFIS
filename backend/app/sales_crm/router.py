"""SalesPilot CRM REST API — /api/sales/*."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.sales_crm.dashboard_schemas import SalesDashboardOut
from app.sales_crm.dashboard_service import SalesDashboardService
from app.sales_crm.pipeline_schemas import PipelineBoardOut, PipelineDrawerOut, PipelineMoveStageIn, PipelineCardOut
from app.sales_crm.pipeline_service import SalesPipelineService
from app.sales_crm.workspace_schemas import RelationshipWorkspaceOut
from app.sales_crm.workspace_service import RelationshipWorkspaceService
from app.sales_crm.deal_schemas import (
    DealProductOut,
    DealWorkspaceOut,
    OpportunityParticipantCreate,
    OpportunityProductCreate,
    OpportunityProductUpdate,
)
from app.sales_crm import deal_service as deal_svc
from app.sales_crm.deal_service import DealWorkspaceService
from app.sales_crm import service as svc
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
from app.sales_crm.permissions import (
    SALES_MANAGE,
    SALES_PIPELINE_MANAGE,
    SALES_READ,
    SALES_WRITE,
)
from app.sales_crm.schemas import (
    ActivityCreate,
    ActivityOut,
    ActivityUpdate,
    AttachmentCreate,
    AttachmentOut,
    BootstrapOut,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    LeadCreate,
    LeadOut,
    LeadUpdate,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    OpportunityCreate,
    OpportunityOut,
    OpportunityUpdate,
    PersonCreate,
    PersonOut,
    PersonUpdate,
    PipelineCreate,
    PipelineOut,
    PipelineStageCreate,
    PipelineStageOut,
    PipelineStageUpdate,
    ReasonOut,
    SalesListResponse,
    TagCreate,
    TagOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

router = APIRouter(prefix="/sales", tags=["sales-crm"])


def _uid(auth: AuthContext) -> int | None:
    return auth.user.id if auth.user else None


@router.get("/dashboard", response_model=SalesDashboardOut)
def sales_dashboard(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Dashboard SalesPilot — agrégation backend unique (aucun KPI frontend)."""
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    payload = SalesDashboardService(db).build(organization_id=org_id, user_id=_uid(auth))
    db.commit()
    return payload


@router.get("/workspace/{entity}/{entity_id}", response_model=RelationshipWorkspaceOut)
def sales_relationship_workspace(
    entity: str,
    entity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Relationship Workspace unifié — lead|company|person|opportunity."""
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    payload = RelationshipWorkspaceService(db).build(
        organization_id=org_id,
        entity=entity,
        entity_id=entity_id,
        user_id=_uid(auth),
        publish_opened=True,
    )
    db.commit()
    return payload


@router.get("/pipeline", response_model=PipelineBoardOut)
def sales_pipeline_board(
    pipeline_id: int | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Pipeline board — colonnes + cartes + summary (une requête)."""
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    board = SalesPipelineService(db).build_board(
        organization_id=org_id, user_id=_uid(auth), pipeline_id=pipeline_id
    )
    db.commit()
    return board


@router.post(
    "/pipeline/opportunities/{opportunity_id}/move",
    response_model=PipelineCardOut,
)
def sales_pipeline_move(
    opportunity_id: int,
    body: PipelineMoveStageIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Déplacement d'étape validé backend — événement stage_changed + rollback client si 409."""
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    card = SalesPipelineService(db).move_stage(
        organization_id=org_id,
        user_id=_uid(auth),
        opportunity_id=opportunity_id,
        stage_id=body.stage_id,
        expected_stage_id=body.expected_stage_id,
    )
    db.commit()
    return card


@router.get(
    "/pipeline/opportunities/{opportunity_id}/drawer",
    response_model=PipelineDrawerOut,
)
def sales_pipeline_drawer(
    opportunity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return SalesPipelineService(db).drawer(
        organization_id=org_id, user_id=_uid(auth), opportunity_id=opportunity_id
    )


@router.get("/bootstrap", response_model=BootstrapOut)
def bootstrap(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    pipeline = svc.ensure_default_pipeline(db, organization_id=org_id, user_id=_uid(auth))
    db.commit()
    db.refresh(pipeline)
    stages = (
        svc.soft_alive(db.query(SalesPipelineStage), SalesPipelineStage)
        .filter(SalesPipelineStage.pipeline_id == pipeline.id)
        .order_by(SalesPipelineStage.position.asc())
        .all()
    )
    lost = (
        svc.soft_alive(db.query(SalesLostReason), SalesLostReason)
        .filter(SalesLostReason.organization_id == org_id)
        .all()
    )
    won = (
        svc.soft_alive(db.query(SalesWinReason), SalesWinReason)
        .filter(SalesWinReason.organization_id == org_id)
        .all()
    )
    pipe_out = PipelineOut.model_validate(pipeline)
    pipe_out.stages = [PipelineStageOut.model_validate(s) for s in stages]
    return BootstrapOut(
        pipeline=pipe_out,
        lost_reasons=[ReasonOut.model_validate(r) for r in lost],
        win_reasons=[ReasonOut.model_validate(r) for r in won],
    )


# ----- Pipelines -----


@router.get("/pipelines", response_model=list[PipelineOut])
def list_pipelines(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    svc.ensure_default_pipeline(db, organization_id=org_id, user_id=_uid(auth))
    db.commit()
    rows = (
        svc.soft_alive(db.query(SalesPipeline), SalesPipeline)
        .filter(SalesPipeline.organization_id == org_id)
        .all()
    )
    out: list[PipelineOut] = []
    for p in rows:
        stages = (
            svc.soft_alive(db.query(SalesPipelineStage), SalesPipelineStage)
            .filter(SalesPipelineStage.pipeline_id == p.id)
            .order_by(SalesPipelineStage.position.asc())
            .all()
        )
        item = PipelineOut.model_validate(p)
        item.stages = [PipelineStageOut.model_validate(s) for s in stages]
        out.append(item)
    return out


@router.post("/pipelines", response_model=PipelineOut, status_code=201)
def create_pipeline(
    body: PipelineCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_PIPELINE_MANAGE)
    org_id = auth.require_organization_id()
    row = SalesPipeline(
        organization_id=org_id,
        created_by=_uid(auth),
        updated_by=_uid(auth),
        **body.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PipelineOut.model_validate(row)


@router.post("/pipelines/{pipeline_id}/stages", response_model=PipelineStageOut, status_code=201)
def create_stage(
    pipeline_id: int,
    body: PipelineStageCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_PIPELINE_MANAGE)
    org_id = auth.require_organization_id()
    svc.get_org_row(db, SalesPipeline, organization_id=org_id, row_id=pipeline_id)
    row = SalesPipelineStage(
        organization_id=org_id,
        pipeline_id=pipeline_id,
        created_by=_uid(auth),
        updated_by=_uid(auth),
        **body.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PipelineStageOut.model_validate(row)


@router.patch("/stages/{stage_id}", response_model=PipelineStageOut)
def update_stage(
    stage_id: int,
    body: PipelineStageUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_PIPELINE_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesPipelineStage, organization_id=org_id, row_id=stage_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_by = _uid(auth)
    db.commit()
    db.refresh(row)
    return PipelineStageOut.model_validate(row)


# ----- Companies -----


@router.get("/companies", response_model=SalesListResponse[CompanyOut])
def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    sort: str = "-updated_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_companies(
        db, organization_id=org_id, page=page, page_size=page_size, q=q, sort=sort
    )
    return SalesListResponse(
        items=[CompanyOut.model_validate(i) for i in items], pagination=pagination
    )


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(
    body: CompanyCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_company(db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump())
    db.commit()
    db.refresh(row)
    return CompanyOut.model_validate(row)


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesCompany, organization_id=org_id, row_id=company_id)
    return CompanyOut.model_validate(row)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    body: CompanyUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesCompany, organization_id=org_id, row_id=company_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_by = _uid(auth)
    db.commit()
    db.refresh(row)
    return CompanyOut.model_validate(row)


@router.delete("/companies/{company_id}", status_code=204)
def delete_company(
    company_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesCompany, organization_id=org_id, row_id=company_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


# ----- People (Contacts) -----


@router.get("/people", response_model=SalesListResponse[PersonOut])
def list_people(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    company_id: int | None = None,
    sort: str = "-updated_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_people(
        db,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        q=q,
        company_id=company_id,
        sort=sort,
    )
    return SalesListResponse(items=[PersonOut.model_validate(i) for i in items], pagination=pagination)


@router.post("/people", response_model=PersonOut, status_code=201)
def create_person(
    body: PersonCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_person(db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump())
    db.commit()
    db.refresh(row)
    return PersonOut.model_validate(row)


@router.get("/people/{person_id}", response_model=PersonOut)
def get_person(
    person_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return PersonOut.model_validate(
        svc.get_org_row(db, SalesPerson, organization_id=org_id, row_id=person_id)
    )


@router.patch("/people/{person_id}", response_model=PersonOut)
def update_person(
    person_id: int,
    body: PersonUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesPerson, organization_id=org_id, row_id=person_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_by = _uid(auth)
    db.commit()
    db.refresh(row)
    return PersonOut.model_validate(row)


@router.delete("/people/{person_id}", status_code=204)
def delete_person(
    person_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesPerson, organization_id=org_id, row_id=person_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


# ----- Leads -----


@router.get("/leads", response_model=SalesListResponse[LeadOut])
def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    sort: str = "-updated_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_leads(
        db, organization_id=org_id, page=page, page_size=page_size, q=q, status=status, sort=sort
    )
    return SalesListResponse(items=[LeadOut.model_validate(i) for i in items], pagination=pagination)


@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(
    body: LeadCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_lead(db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump())
    db.commit()
    db.refresh(row)
    return LeadOut.model_validate(row)


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return LeadOut.model_validate(svc.get_org_row(db, SalesLead, organization_id=org_id, row_id=lead_id))


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    body: LeadUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesLead, organization_id=org_id, row_id=lead_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_by = _uid(auth)
    db.commit()
    db.refresh(row)
    return LeadOut.model_validate(row)


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesLead, organization_id=org_id, row_id=lead_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


# ----- Opportunities -----


@router.get("/opportunities", response_model=SalesListResponse[OpportunityOut])
def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    pipeline_id: int | None = None,
    stage_id: int | None = None,
    sort: str = "-updated_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_opportunities(
        db,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        sort=sort,
    )
    return SalesListResponse(
        items=[OpportunityOut.model_validate(i) for i in items], pagination=pagination
    )


@router.post("/opportunities", response_model=OpportunityOut, status_code=201)
def create_opportunity(
    body: OpportunityCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_opportunity(
        db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump(exclude_unset=True)
    )
    db.commit()
    db.refresh(row)
    return OpportunityOut.model_validate(row)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityOut)
def get_opportunity(
    opportunity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return OpportunityOut.model_validate(
        svc.get_org_row(db, SalesOpportunity, organization_id=org_id, row_id=opportunity_id)
    )


@router.get("/opportunities/{opportunity_id}/workspace", response_model=DealWorkspaceOut)
def sales_deal_workspace(
    opportunity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Deal Workspace — cockpit commercial d'une opportunité (S1.5)."""
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    payload = DealWorkspaceService(db).build(
        organization_id=org_id,
        opportunity_id=opportunity_id,
        user_id=_uid(auth),
        publish_opened=True,
    )
    db.commit()
    return payload


@router.post(
    "/opportunities/{opportunity_id}/products",
    response_model=DealProductOut,
    status_code=201,
)
def add_opportunity_product(
    opportunity_id: int,
    body: OpportunityProductCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = deal_svc.add_product(
        db,
        organization_id=org_id,
        user_id=_uid(auth),
        opportunity_id=opportunity_id,
        data=body.model_dump(),
    )
    db.commit()
    db.refresh(row)
    return DealProductOut(
        id=row.id,
        name=row.name,
        description=row.description,
        quantity=row.quantity,
        unit_price=row.unit_price,
        discount_percent=row.discount_percent,
        line_total=row.line_total,
        position=row.position,
    )


@router.patch(
    "/opportunities/{opportunity_id}/products/{product_id}",
    response_model=DealProductOut,
)
def update_opportunity_product(
    opportunity_id: int,
    product_id: int,
    body: OpportunityProductUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = deal_svc.update_product(
        db,
        organization_id=org_id,
        user_id=_uid(auth),
        opportunity_id=opportunity_id,
        product_id=product_id,
        data=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(row)
    return DealProductOut(
        id=row.id,
        name=row.name,
        description=row.description,
        quantity=row.quantity,
        unit_price=row.unit_price,
        discount_percent=row.discount_percent,
        line_total=row.line_total,
        position=row.position,
    )


@router.delete("/opportunities/{opportunity_id}/products/{product_id}", status_code=204)
def delete_opportunity_product(
    opportunity_id: int,
    product_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    deal_svc.remove_product(
        db,
        organization_id=org_id,
        user_id=_uid(auth),
        opportunity_id=opportunity_id,
        product_id=product_id,
    )
    db.commit()


@router.post("/opportunities/{opportunity_id}/participants", status_code=201)
def add_opportunity_participant(
    opportunity_id: int,
    body: OpportunityParticipantCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = deal_svc.add_participant(
        db,
        organization_id=org_id,
        user_id=_uid(auth),
        opportunity_id=opportunity_id,
        data=body.model_dump(),
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "opportunity_id": row.opportunity_id,
        "person_id": row.person_id,
        "role": row.role,
        "is_primary": row.is_primary,
    }


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityOut)
def update_opportunity(
    opportunity_id: int,
    body: OpportunityUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.update_opportunity(
        db,
        organization_id=org_id,
        user_id=_uid(auth),
        opportunity_id=opportunity_id,
        data=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(row)
    return OpportunityOut.model_validate(row)


@router.delete("/opportunities/{opportunity_id}", status_code=204)
def delete_opportunity(
    opportunity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesOpportunity, organization_id=org_id, row_id=opportunity_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


# ----- Activities -----


@router.get("/activities", response_model=SalesListResponse[ActivityOut])
def list_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    activity_type: str | None = None,
    opportunity_id: int | None = None,
    sort: str = "-activity_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_activities(
        db,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        q=q,
        activity_type=activity_type,
        opportunity_id=opportunity_id,
        sort=sort,
    )
    return SalesListResponse(
        items=[ActivityOut.model_validate(i) for i in items], pagination=pagination
    )


@router.post("/activities", response_model=ActivityOut, status_code=201)
def create_activity(
    body: ActivityCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_activity(
        db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump(exclude_unset=True)
    )
    db.commit()
    db.refresh(row)
    return ActivityOut.model_validate(row)


@router.patch("/activities/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesActivity, organization_id=org_id, row_id=activity_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_by = _uid(auth)
    db.commit()
    db.refresh(row)
    return ActivityOut.model_validate(row)


@router.delete("/activities/{activity_id}", status_code=204)
def delete_activity(
    activity_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesActivity, organization_id=org_id, row_id=activity_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


# ----- Tasks -----


@router.get("/tasks", response_model=SalesListResponse[TaskOut])
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    opportunity_id: int | None = None,
    sort: str = "-updated_at",
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_tasks(
        db,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
        opportunity_id=opportunity_id,
        sort=sort,
    )
    return SalesListResponse(items=[TaskOut.model_validate(i) for i in items], pagination=pagination)


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    body: TaskCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_task(db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump())
    db.commit()
    db.refresh(row)
    return TaskOut.model_validate(row)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesTask, organization_id=org_id, row_id=task_id)
    return TaskOut.model_validate(row)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    body: TaskUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.update_task(
        db,
        organization_id=org_id,
        user_id=_uid(auth),
        task_id=task_id,
        data=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(row)
    return TaskOut.model_validate(row)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesTask, organization_id=org_id, row_id=task_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


# ----- Notes / Tags / Attachments -----


@router.get("/notes", response_model=SalesListResponse[NoteOut])
def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    entity_id: int | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    items, pagination = svc.list_notes(
        db,
        organization_id=org_id,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return SalesListResponse(items=[NoteOut.model_validate(i) for i in items], pagination=pagination)


@router.post("/notes", response_model=NoteOut, status_code=201)
def create_note(
    body: NoteCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_note(db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump())
    db.commit()
    db.refresh(row)
    return NoteOut.model_validate(row)


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    body: NoteUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesNote, organization_id=org_id, row_id=note_id)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    if hasattr(row, "updated_by"):
        row.updated_by = _uid(auth)
    if hasattr(row, "updated_at"):
        from datetime import datetime

        row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return NoteOut.model_validate(row)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesNote, organization_id=org_id, row_id=note_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()


@router.get("/tags", response_model=list[TagOut])
def list_tags(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth.require(SALES_READ)
    org_id = auth.require_organization_id()
    return [TagOut.model_validate(t) for t in svc.list_tags(db, organization_id=org_id)]


@router.post("/tags", response_model=TagOut, status_code=201)
def create_tag(
    body: TagCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_tag(db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump())
    db.commit()
    db.refresh(row)
    return TagOut.model_validate(row)


@router.post("/attachments", response_model=AttachmentOut, status_code=201)
def create_attachment(
    body: AttachmentCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_WRITE)
    org_id = auth.require_organization_id()
    row = svc.create_attachment(
        db, organization_id=org_id, user_id=_uid(auth), data=body.model_dump()
    )
    db.commit()
    db.refresh(row)
    return AttachmentOut.model_validate(row)


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require(SALES_MANAGE)
    org_id = auth.require_organization_id()
    row = svc.get_org_row(db, SalesAttachment, organization_id=org_id, row_id=attachment_id)
    svc.soft_delete(row, user_id=_uid(auth))
    db.commit()
