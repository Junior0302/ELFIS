"""Sales Operations — Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ResourceType = Literal[
    "leads",
    "companies",
    "people",
    "opportunities",
    "tasks",
    "activities",
    "proposals",
    "notes",
]


class SavedViewCreate(BaseModel):
    resource: ResourceType
    name: str = Field(min_length=1, max_length=120)
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: str | None = None
    is_default: bool = False
    is_shared: bool = False


class SavedViewUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    filters: dict[str, Any] | None = None
    sort: str | None = None
    is_default: bool | None = None
    is_shared: bool | None = None


class SavedViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource: str
    name: str
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: str | None = None
    is_default: bool
    is_shared: bool
    owner_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class BulkActionIn(BaseModel):
    resource: ResourceType
    action: Literal[
        "assign",
        "change_stage",
        "add_tag",
        "soft_delete",
        "archive",
        "mark_done",
        "close_lost",
        "close_won",
    ]
    ids: list[int] = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False


class BulkActionOut(BaseModel):
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class CalendarQuery(BaseModel):
    from_date: date
    to_date: date
    include_tasks: bool = True
    include_activities: bool = True
    include_closings: bool = True
    include_proposals: bool = True


class CalendarEventOut(BaseModel):
    id: str
    event_type: str
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    source_type: str
    source_id: int
    route: str
    severity: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class CalendarOut(BaseModel):
    events: list[CalendarEventOut]
    from_date: date
    to_date: date
    generated_at: datetime


class ImportPreviewIn(BaseModel):
    resource: Literal["leads", "companies", "people"]
    csv_text: str = Field(min_length=1, max_length=2_000_000)
    delimiter: str = ","


class ImportPreviewRow(BaseModel):
    row_number: int
    data: dict[str, Any]
    status: Literal["ok", "error", "duplicate"]
    messages: list[str] = Field(default_factory=list)
    duplicate_of_id: int | None = None


class ImportPreviewOut(BaseModel):
    resource: str
    columns_detected: list[str]
    column_mapping: dict[str, str]
    rows: list[ImportPreviewRow]
    ok_count: int
    error_count: int
    duplicate_count: int


class ImportCommitIn(BaseModel):
    resource: Literal["leads", "companies", "people"]
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=500)
    skip_duplicates: bool = True


class ImportCommitOut(BaseModel):
    created: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class DuplicateCandidateOut(BaseModel):
    resource: str
    record_id: int
    label: str
    match_level: Literal["exact", "possible"]
    matched_on: list[str]
    record: dict[str, Any]


class DuplicateScanOut(BaseModel):
    resource: str
    groups: list[list[DuplicateCandidateOut]]
    scanned: int
    generated_at: datetime


class DuplicateResolveIn(BaseModel):
    resource: ResourceType
    primary_id: int
    secondary_id: int
    action: Literal["ignore", "link", "manual_merge_prepare"]
    note: str | None = None


class JournalItemOut(BaseModel):
    id: str
    kind: str
    title: str
    summary: str | None = None
    occurred_at: datetime
    source_type: str
    source_id: int | None = None
    route: str | None = None


class JournalOut(BaseModel):
    items: list[JournalItemOut]
    generated_at: datetime


class NoteUpdate(BaseModel):
    body_markdown: str | None = Field(default=None, min_length=1)
