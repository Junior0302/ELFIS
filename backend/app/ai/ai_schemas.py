"""Schémas Pydantic — ELFIS AI Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AIExecutionRequest(BaseModel):
    task_name: str
    task_version: int = 1
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    input_reference_type: Optional[str] = None
    input_reference_id: Optional[str] = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None
    source_event_id: Optional[str] = None


class AIUsageSummary(BaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None
    currency: str = "USD"


class AIExecutionResult(BaseModel):
    execution_id: str
    status: str
    task_name: str
    provider: str
    model: str
    result: Optional[dict[str, Any]] = None
    requires_review: bool = False
    confidence: Optional[float] = None
    usage: AIUsageSummary = Field(default_factory=AIUsageSummary)
    latency_ms: Optional[int] = None
    created: bool = True
    idempotent_reuse: bool = False


class AIProviderResponse(BaseModel):
    content: str = ""
    structured_output: Optional[dict[str, Any]] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    provider_request_id: Optional[str] = None


class DocumentAnalyzeRequest(BaseModel):
    """Corps optionnel — extracted_text depuis source interne contrôlée (pas d'OCR fictif)."""

    extracted_text: Optional[str] = None
    filename: Optional[str] = None


class DocumentAnalyzeAccepted(BaseModel):
    analysis_id: str
    vault_document_id: str
    status: str
    current_stage: Optional[str] = None
    job_id: Optional[str] = None
    reused_existing_analysis: bool = False


class DocumentAnalysisView(BaseModel):
    analysis_id: str
    status: str
    current_stage: Optional[str] = None
    document_type: Optional[str] = None
    confidence: Optional[float] = None
    requires_review: bool = False
    quality_summary: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
