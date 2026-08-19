"""Deal Workspace V1 — response schemas (S1.5)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ParticipantRole = Literal[
    "decision_maker",
    "influencer",
    "technical",
    "buyer",
    "primary",
]


class DealHeaderOut(BaseModel):
    opportunity_id: int
    name: str
    company_id: int | None = None
    company_name: str | None = None
    amount: Decimal | None = None
    pipeline_id: int | None = None
    pipeline_name: str | None = None
    stage_id: int | None = None
    stage_name: str | None = None
    owner_label: str | None = None
    probability: int = 0
    status: str = "open"
    health_score: int = 0
    health_label: str = "Critique"
    health_explanation: str = ""
    relationship_score: int = 0
    relationship_label: str = "Fragile"
    risk_level: str = "medium"
    risk_label: str = "Medium"
    forecast_amount: Decimal = Decimal("0")
    forecast_label: str = "Prévision pondérée"
    last_activity_at: datetime | None = None
    expected_close_date: date | None = None
    created_at: datetime | None = None


class DealSummaryOut(BaseModel):
    participants_count: int = 0
    products_count: int = 0
    products_total: Decimal = Decimal("0")
    activities_count: int = 0
    open_tasks_count: int = 0
    notes_count: int = 0
    documents_count: int = 0
    forecast_amount: Decimal = Decimal("0")


class DealParticipantOut(BaseModel):
    id: int | None = None  # None when derived from opportunity.person_id
    person_id: int
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None
    role: ParticipantRole
    role_label: str
    is_primary: bool = False
    href: str


class DealProductOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal
    line_total: Decimal
    position: int = 0


class DealActivityOut(BaseModel):
    id: int
    activity_type: str
    subject: str
    activity_at: datetime
    result: str | None = None
    owner_label: str | None = None


class DealTaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_at: datetime | None = None
    bucket: str


class DealNoteOut(BaseModel):
    id: int
    body_markdown: str
    author_user_id: int | None = None
    author_label: str | None = None
    created_at: datetime


class DealAttachmentOut(BaseModel):
    id: int
    vault_document_id: int
    label: str | None = None
    filename: str | None = None
    preview_url: str | None = None
    open_url: str | None = None


class DealTimelineItemOut(BaseModel):
    id: str
    event_type: str
    title: str
    occurred_at: datetime
    meta: dict[str, str] = Field(default_factory=dict)


class DealHealthOut(BaseModel):
    score: int
    label: str
    explanation: str
    risk_level: str
    risk_label: str


class DealRelationshipOut(BaseModel):
    score: int
    label: str
    explanation: str
    factors: list[str] = Field(default_factory=list)


class DealForecastOut(BaseModel):
    amount: Decimal
    probability: int
    weighted_amount: Decimal
    label: str = "Prévision pondérée"
    formula: str = "montant × probabilité"


class DealQuickActionOut(BaseModel):
    id: str
    label: str
    href: str


class DealWorkspaceOut(BaseModel):
    header: DealHeaderOut
    summary: DealSummaryOut
    participants: list[DealParticipantOut] = Field(default_factory=list)
    products: list[DealProductOut] = Field(default_factory=list)
    activities: list[DealActivityOut] = Field(default_factory=list)
    tasks: list[DealTaskOut] = Field(default_factory=list)
    notes: list[DealNoteOut] = Field(default_factory=list)
    attachments: list[DealAttachmentOut] = Field(default_factory=list)
    timeline: list[DealTimelineItemOut] = Field(default_factory=list)
    health: DealHealthOut
    relationship: DealRelationshipOut
    forecast: DealForecastOut
    quick_actions: list[DealQuickActionOut] = Field(default_factory=list)
    generated_at: datetime


# ----- Product / participant write schemas -----


class OpportunityProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    position: int = 0


class OpportunityProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100)
    position: int | None = None


class OpportunityParticipantCreate(BaseModel):
    person_id: int
    role: ParticipantRole = "primary"
    is_primary: bool = False


class OpportunityParticipantUpdate(BaseModel):
    role: ParticipantRole | None = None
    is_primary: bool | None = None
