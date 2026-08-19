"""SalesPilot Collaboration V1 — schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


EntityType = Literal[
    "lead",
    "company",
    "person",
    "opportunity",
    "proposal",
    "activity",
    "task",
    "workspace",
]

AssignResource = Literal["lead", "opportunity", "task", "proposal", "activity"]


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    lead_user_id: int | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    lead_user_id: int | None = None
    status: Literal["active", "archived"] | None = None


class TeamMemberIn(BaseModel):
    user_id: int
    role: Literal["lead", "manager", "member", "viewer"] = "member"
    permissions: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0


class TeamMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    user_id: int
    role: str
    permissions: dict[str, Any] = Field(default_factory=dict)
    sort_order: int
    status: str
    user_label: str | None = None


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    lead_user_id: int | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    members: list[TeamMemberOut] = Field(default_factory=list)


class AssignIn(BaseModel):
    resource: AssignResource
    resource_id: int
    owner_user_id: int
    comment: str | None = None


class AssignOut(BaseModel):
    resource: str
    resource_id: int
    previous_owner_user_id: int | None = None
    owner_user_id: int
    assigned_at: datetime


class CommentCreate(BaseModel):
    entity_type: EntityType
    entity_id: int
    body: str = Field(min_length=1, max_length=8000)
    vault_document_ids: list[int] = Field(default_factory=list)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    vault_document_ids: list[int] | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    author_user_id: int | None
    author_label: str | None = None
    body: str
    mentions: list[dict[str, Any]] = Field(default_factory=list)
    vault_document_ids: list[int] = Field(default_factory=list)
    edited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FollowIn(BaseModel):
    entity_type: EntityType
    entity_id: int


class FollowerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    user_id: int
    user_label: str | None = None
    created_at: datetime


class ReviewCreate(BaseModel):
    entity_type: Literal["opportunity", "proposal", "workspace"]
    entity_id: int
    reviewer_user_id: int
    message: str | None = None


class ReviewDecide(BaseModel):
    decision: Literal["approved", "changes_requested", "rejected"]
    decision_comment: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    requester_user_id: int | None
    reviewer_user_id: int
    status: str
    message: str | None = None
    decision_comment: str | None = None
    decided_at: datetime | None = None
    created_at: datetime
    route: str | None = None


class TransferIn(BaseModel):
    entity_type: EntityType
    entity_id: int
    to_user_id: int
    reason: str = Field(min_length=1, max_length=120)
    comment: str | None = None


class TransferOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    from_user_id: int | None
    to_user_id: int
    reason: str
    comment: str | None = None
    created_at: datetime


class CollabViewQuery(BaseModel):
    view: Literal["mine", "team", "assigned", "following", "to_review"] = "mine"
    resource: Literal["leads", "opportunities", "tasks", "proposals", "activities"] = "opportunities"
    team_id: int | None = None
    page: int = 1
    page_size: int = 20


class TeamDashboardOut(BaseModel):
    team_id: int | None
    team_name: str | None
    open_opportunities: int
    pipeline_value: float
    overdue_tasks: int
    open_tasks: int
    pending_reviews: int
    members: list[dict[str, Any]] = Field(default_factory=list)
    load_by_member: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime


class MentionCandidate(BaseModel):
    user_id: int
    label: str
    email: str | None = None
