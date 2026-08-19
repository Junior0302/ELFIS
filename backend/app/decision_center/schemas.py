"""Schémas API Decision Center + Execution Layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DecisionActionOut(BaseModel):
    """Actions V2 — le frontend ne doit pas inventer routes ni méthodes."""

    action_type: str
    type: str | None = None  # alias compat C1.15
    label: str
    description: str | None = None
    method: Literal["NAVIGATE", "POST"] = "NAVIGATE"
    endpoint: str | None = None
    action_path: str | None = None
    path: str | None = None  # alias compat C1.15
    requires_confirmation: bool = False
    destructive: bool = False
    required_permission: str | None = None
    enabled: bool = True
    disabled_reason: str | None = None
    idempotency_supported: bool = False
    opens_external_page: bool = False
    opens_source: bool = False
    expected_resolution_behavior: str | None = None

    @model_validator(mode="after")
    def _aliases(self) -> DecisionActionOut:
        object.__setattr__(self, "type", self.type or self.action_type)
        object.__setattr__(self, "path", self.path if self.path is not None else self.action_path)
        return self


class DecisionEvidenceOut(BaseModel):
    type: str
    label: str
    value: str | None = None
    description: str | None = None


class DecisionHistoryItemOut(BaseModel):
    id: str
    kind: str
    label: str
    status: str | None = None
    action_type: str | None = None
    at: datetime
    user_id: int | None = None
    error_message: str | None = None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: int
    decision_type: str
    source_type: str
    source_id: str
    status: str
    severity: str
    confidence: float | None = None
    title: str
    summary: str
    explanation: str
    recommended_action_type: str
    recommended_action_path: str | None = None
    required_permission: str | None = None
    created_by_rule: str
    rule_version: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    dismissed_at: datetime | None = None
    available_actions: list[DecisionActionOut] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None
    execution_status: str = "idle"
    last_action_type: str | None = None
    last_execution_error_code: str | None = None
    last_execution_error_message: str | None = None
    execution_attempts: int = 0
    last_source_refresh_at: datetime | None = None


class DecisionDetailOut(DecisionOut):
    evidence: list[DecisionEvidenceOut] = Field(default_factory=list)
    history: list[DecisionHistoryItemOut] = Field(default_factory=list)
    source_label: str | None = None
    what_was_detected: str | None = None
    why_it_matters: str | None = None
    what_to_do: str | None = None
    what_happens_after: str | None = None


class DecisionListOut(BaseModel):
    items: list[DecisionOut]
    total: int
    page: int
    page_size: int


class DecisionMutationOut(BaseModel):
    ok: bool = True
    decision: DecisionOut


class DecisionExecuteRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)
    comment: str | None = Field(default=None, max_length=2000)
    confirm_balanced_entry: bool = False
    confirm_document_reviewed: bool = False


class DecisionExecuteResultOut(BaseModel):
    execution_id: str | None = None
    action_type: str
    status: str
    navigation_path: str | None = None
    message: str | None = None
    error_code: str | None = None
    source_status: str | None = None


class DecisionExecuteOut(BaseModel):
    ok: bool = True
    decision: DecisionDetailOut
    result: DecisionExecuteResultOut


class CommandDecisionInsightOut(BaseModel):
    decision_id: str
    title: str
    summary: str
    severity: str
    action_label: str
    action_path: str | None = None
