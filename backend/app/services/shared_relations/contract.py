"""Shared Relations contract — ELFIS Core projection (S1.2).

No physical Party table yet. Opaque IDs: customer:N | contact:N | sales_company:N
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

PartyType = Literal["person", "organization", "unknown"]
RelationRole = Literal[
    "customer",
    "supplier",
    "prospect",
    "partner",
    "employee",
    "commercial_account",
    "billing_contact",
]
SourceSystem = Literal["customer", "contact", "sales_company"]
RelationStatus = Literal["active", "inactive", "archived", "unknown"]


class SharedAddress(BaseModel):
    line1: str = ""
    line2: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = ""


class SharedRelation(BaseModel):
    id: str
    organization_id: int
    party_type: PartyType = "unknown"
    display_name: str
    legal_name: str = ""
    first_name: str = ""
    last_name: str = ""
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    addresses: list[SharedAddress] = Field(default_factory=list)
    tax_number: str = ""
    siren: str = ""
    siret: str = ""
    roles: list[RelationRole] = Field(default_factory=list)
    status: RelationStatus = "active"
    source_system: SourceSystem
    source_entity_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Pilot deep-links (read-only convenience)
    links: dict[str, str] = Field(default_factory=dict)


class PossibleDuplicate(BaseModel):
    possible_duplicate: bool = True
    confidence: float
    matching_fields: list[str]
    related_entity_ids: list[str]
    left_id: str
    right_id: str


class SharedRelationListResponse(BaseModel):
    items: list[SharedRelation]
    total: int
    page: int
    page_size: int
    total_pages: int


class SharedRelationDetail(BaseModel):
    relation: SharedRelation
    roles: list[RelationRole]
    usages: dict[str, Any] = Field(default_factory=dict)
    duplicates: list[PossibleDuplicate] = Field(default_factory=list)


def make_relation_id(source_system: SourceSystem, entity_id: int) -> str:
    return f"{source_system}:{int(entity_id)}"


def parse_relation_id(relation_id: str) -> tuple[SourceSystem, int]:
    raw = (relation_id or "").strip()
    if ":" not in raw:
        raise ValueError("invalid_relation_id")
    source, _, id_part = raw.partition(":")
    if source not in ("customer", "contact", "sales_company"):
        raise ValueError("invalid_source_system")
    entity_id = int(id_part)
    if entity_id <= 0:
        raise ValueError("invalid_entity_id")
    return source, entity_id  # type: ignore[return-value]
