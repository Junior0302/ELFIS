"""Schémas API Accounting Engine V2."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateIn(BaseModel):
    payload: dict[str, Any] | None = None
    invoice_id: int | None = None
    source_document_id: str | None = None
    source_kind: str = "manual"


class RegenerateIn(BaseModel):
    proposal_id: str
    payload_overrides: dict[str, Any] | None = None


class ProposalOut(BaseModel):
    data: dict[str, Any]


class ConfidenceOut(BaseModel):
    proposal_id: str
    score: float | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class ExplanationOut(BaseModel):
    data: dict[str, Any]
