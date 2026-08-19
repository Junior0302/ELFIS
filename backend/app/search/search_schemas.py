"""Schémas Search Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchIndexRequest(BaseModel):
    organization_id: int
    resource_type: str
    resource_id: str
    resource_version: int = 1
    source_event_id: Optional[str] = None
    correlation_id: Optional[str] = None
    force_reindex: bool = False
    user_id: Optional[int] = None


class SearchQuery(BaseModel):
    query: Optional[str] = None
    resource_types: Optional[list[str]] = None
    statuses: Optional[list[str]] = None
    categories: Optional[list[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    currency: Optional[str] = None
    requires_review: Optional[bool] = None
    page: int = 1
    page_size: int = 20
    sort: Optional[str] = None


class SearchResultItem(BaseModel):
    search_document_id: str
    resource_type: str
    resource_id: str
    title: str
    subtitle: Optional[str] = None
    snippet: str = ""
    status: Optional[str] = None
    category: Optional[str] = None
    document_date: Optional[datetime] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    action_url: Optional[str] = None
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    items: list[SearchResultItem] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0
    query: Optional[str] = None
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: int = 0


class SearchIndexResult(BaseModel):
    search_document_id: str
    resource_type: str
    resource_id: str
    status: str
    indexed: bool = True
    created: bool = False


class BuiltSearchDocument(BaseModel):
    """Document d'index construit par un indexer (avant persistance)."""

    organization_id: int
    user_id: Optional[int] = None
    resource_type: str
    resource_id: str
    resource_version: int = 1
    title: str
    subtitle: Optional[str] = None
    content: Optional[str] = None
    search_text: str
    status: Optional[str] = None
    category: Optional[str] = None
    document_date: Optional[datetime] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    action_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""


class SuggestionItem(BaseModel):
    title: str
    resource_type: str
    resource_id: str
    action_url: Optional[str] = None
