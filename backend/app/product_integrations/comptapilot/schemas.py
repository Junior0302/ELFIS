"""Schémas transport ComptaPilot (pas de modèles comptables)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComptaPilotTransportDocument(BaseModel):
    schema_key: str = Field(default="comptapilot_document_import_transport_v1")
    organization_id: int | None = None
    document: dict[str, Any] | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    validation_status: str | None = None
    issue_codes: list[str] = Field(default_factory=list)
