"""Relationship Workspace V1 — response schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

WorkspaceEntity = Literal["lead", "company", "person", "opportunity"]


class WorkspaceHeaderOut(BaseModel):
    entity: WorkspaceEntity
    entity_id: int
    name: str
    status: str | None = None
    pipeline_name: str | None = None
    stage_name: str | None = None
    amount: Decimal | None = None
    owner_label: str | None = None
    created_at: datetime | None = None
    last_activity_at: datetime | None = None
    health_score: int = 0
    health_label: str = "Critique"
    health_explanation: str = ""
    relationship_score: int = 0
    relationship_label: str = "Fragile"
    risk_level: str = "medium"
    risk_label: str = "Medium"


class WorkspaceSummaryOut(BaseModel):
    open_opportunities: int = 0
    contacts_count: int = 0
    activities_count: int = 0
    open_tasks_count: int = 0
    notes_count: int = 0
    documents_count: int = 0
    pipeline_value: Decimal = Decimal("0")


class WorkspaceContactOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None
    is_primary: bool = False
    linkedin_url: str | None = None  # prepared — not stored yet


class WorkspaceOpportunityOut(BaseModel):
    id: int
    name: str
    stage_name: str | None = None
    estimated_amount: Decimal | None = None
    probability: int = 0
    owner_label: str | None = None
    health_score: int = 0
    health_label: str = ""
    status: str = "open"
    href: str


class WorkspaceActivityOut(BaseModel):
    id: int
    activity_type: str
    subject: str
    activity_at: datetime
    result: str | None = None
    owner_label: str | None = None


class WorkspaceTaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_at: datetime | None = None
    bucket: str  # overdue | today | upcoming | other


class WorkspaceNoteOut(BaseModel):
    id: int
    body_markdown: str
    author_user_id: int | None = None
    author_label: str | None = None
    created_at: datetime


class WorkspaceAttachmentOut(BaseModel):
    id: int
    vault_document_id: str
    label: str | None = None
    filename: str | None = None
    preview_url: str | None = None
    open_url: str | None = None


class WorkspaceTimelineItemOut(BaseModel):
    id: str
    event_type: str
    title: str
    occurred_at: datetime
    meta: dict[str, str] = Field(default_factory=dict)


class WorkspaceHealthOut(BaseModel):
    score: int
    label: str
    explanation: str
    risk_level: str
    risk_label: str


class WorkspaceRelationshipOut(BaseModel):
    score: int
    label: str
    explanation: str
    factors: list[str] = Field(default_factory=list)


class WorkspaceQuickActionOut(BaseModel):
    id: str
    label: str
    href: str


class RelationshipWorkspaceOut(BaseModel):
    header: WorkspaceHeaderOut
    summary: WorkspaceSummaryOut
    contacts: list[WorkspaceContactOut] = Field(default_factory=list)
    opportunities: list[WorkspaceOpportunityOut] = Field(default_factory=list)
    activities: list[WorkspaceActivityOut] = Field(default_factory=list)
    tasks: list[WorkspaceTaskOut] = Field(default_factory=list)
    notes: list[WorkspaceNoteOut] = Field(default_factory=list)
    attachments: list[WorkspaceAttachmentOut] = Field(default_factory=list)
    timeline: list[WorkspaceTimelineItemOut] = Field(default_factory=list)
    health: WorkspaceHealthOut
    relationship: WorkspaceRelationshipOut
    quick_actions: list[WorkspaceQuickActionOut] = Field(default_factory=list)
    generated_at: datetime
