"""Pydantic schemas — SalesPilot CRM V1."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SalesPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class SalesListResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: SalesPagination


# ----- Pipeline -----


class PipelineStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline_id: int
    name: str
    code: str
    position: int
    probability: int
    is_won: bool
    is_lost: bool
    is_active: bool


class PipelineStageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=64)
    position: int = 0
    probability: int = Field(default=0, ge=0, le=100)
    is_won: bool = False
    is_lost: bool = False


class PipelineStageUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    is_won: bool | None = None
    is_lost: bool | None = None
    is_active: bool | None = None


class PipelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_default: bool
    is_active: bool
    stages: list[PipelineStageOut] = []


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=64)
    is_default: bool = False


# ----- Company / Person / Lead -----


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trade_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    industry: str | None = None
    address_line: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    owner_user_id: int | None = None
    source: str | None = None
    status: str = "active"


class CompanyUpdate(BaseModel):
    name: str | None = None
    trade_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    industry: str | None = None
    address_line: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    owner_user_id: int | None = None
    source: str | None = None
    status: str | None = None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    trade_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    siret: str | None = None
    industry: str | None = None
    city: str | None = None
    country: str | None = None
    owner_user_id: int | None = None
    source: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class PersonCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    company_id: int | None = None
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None
    owner_user_id: int | None = None
    status: str = "active"


class PersonUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    company_id: int | None = None
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None
    owner_user_id: int | None = None
    status: str | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    company_id: int | None = None
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None
    owner_user_id: int | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: str = "new"
    source: str | None = None
    priority: str = "medium"
    company_name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    estimated_amount: Decimal | None = None
    owner_user_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    description: str | None = None


class LeadUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    source: str | None = None
    priority: str | None = None
    company_name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    estimated_amount: Decimal | None = None
    owner_user_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    description: str | None = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    source: str | None = None
    priority: str
    company_name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    estimated_amount: Decimal | None = None
    owner_user_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    converted_opportunity_id: int | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime


# ----- Opportunity -----


class OpportunityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    estimated_amount: Decimal | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    pipeline_id: int | None = None
    stage_id: int | None = None
    expected_close_date: date | None = None
    owner_user_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    lead_id: int | None = None
    source: str | None = None
    priority: str = "medium"
    status: str = "open"
    description: str | None = None
    quote_document_id: int | None = None


class OpportunityUpdate(BaseModel):
    name: str | None = None
    estimated_amount: Decimal | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    pipeline_id: int | None = None
    stage_id: int | None = None
    expected_close_date: date | None = None
    owner_user_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    source: str | None = None
    priority: str | None = None
    status: str | None = None
    lost_reason_id: int | None = None
    win_reason_id: int | None = None
    description: str | None = None
    quote_document_id: int | None = None


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    estimated_amount: Decimal | None = None
    probability: int
    pipeline_id: int
    stage_id: int
    expected_close_date: date | None = None
    owner_user_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    lead_id: int | None = None
    source: str | None = None
    priority: str
    status: str
    lost_reason_id: int | None = None
    win_reason_id: int | None = None
    description: str | None = None
    quote_document_id: int | None = None
    created_at: datetime
    updated_at: datetime


# ----- Activity / Task / Note / Tag / Attachment -----


class ActivityCreate(BaseModel):
    activity_type: str = Field(min_length=1, max_length=32)
    subject: str = Field(min_length=1, max_length=200)
    activity_at: datetime | None = None
    owner_user_id: int | None = None
    result: str | None = None
    comment: str | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    lead_id: int | None = None


class ActivityUpdate(BaseModel):
    activity_type: str | None = None
    subject: str | None = None
    activity_at: datetime | None = None
    owner_user_id: int | None = None
    result: str | None = None
    comment: str | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    lead_id: int | None = None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_type: str
    subject: str
    activity_at: datetime
    owner_user_id: int | None = None
    result: str | None = None
    comment: str | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    lead_id: int | None = None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_at: datetime | None = None
    priority: str = "medium"
    status: str = "todo"
    assignee_user_id: int | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_at: datetime | None = None
    priority: str | None = None
    status: str | None = None
    assignee_user_id: int | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    due_at: datetime | None = None
    priority: str
    status: str
    assignee_user_id: int | None = None
    opportunity_id: int | None = None
    company_id: int | None = None
    person_id: int | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    body_markdown: str = Field(min_length=1)
    entity_type: str = Field(min_length=1, max_length=32)
    entity_id: int


class NoteUpdate(BaseModel):
    body_markdown: str | None = Field(default=None, min_length=1)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body_markdown: str
    entity_type: str
    entity_id: int
    author_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#64748b", max_length=32)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    created_at: datetime


class AttachmentCreate(BaseModel):
    vault_document_id: int
    entity_type: str = Field(min_length=1, max_length=32)
    entity_id: int
    label: str | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vault_document_id: int
    entity_type: str
    entity_id: int
    label: str | None = None
    created_at: datetime


class ReasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    is_active: bool


class BootstrapOut(BaseModel):
    pipeline: PipelineOut
    lost_reasons: list[ReasonOut]
    win_reasons: list[ReasonOut]
