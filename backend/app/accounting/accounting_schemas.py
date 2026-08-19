"""Schémas Accounting Pipeline."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class AccountingPipelineRequest(BaseModel):
    organization_id: int
    user_id: Optional[int] = None
    vault_document_id: str
    document_analysis_id: Optional[str] = None
    document_version: Optional[int] = None
    correlation_id: Optional[str] = None
    source_event_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    job_id: Optional[str] = None


class AccountingProposalResult(BaseModel):
    proposal_id: str
    created: bool = True
    status: str
    current_stage: str
    requires_review: bool = False
    confidence: Optional[float] = None
    entry_id: Optional[str] = None
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    financial_summary: dict[str, Any] = Field(default_factory=dict)
    mapping_summary: dict[str, Any] = Field(default_factory=dict)


class AccountingEntryLineIn(BaseModel):
    account_code: str
    account_label: Optional[str] = None
    third_party_name: Optional[str] = None
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    vat_rate: Optional[Decimal] = None
    vat_code: Optional[str] = None
    description: Optional[str] = None


class AccountingProposalUpdate(BaseModel):
    document_number: Optional[str] = None
    document_date: Optional[date] = None
    due_date: Optional[date] = None
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    amount_ht: Optional[Decimal] = None
    amount_vat: Optional[Decimal] = None
    amount_ttc: Optional[Decimal] = None
    currency: Optional[str] = None
    journal_code: Optional[str] = None
    description: Optional[str] = None
    lines: Optional[list[AccountingEntryLineIn]] = None
    comment: Optional[str] = None


class AccountingValidationRequest(BaseModel):
    comment: Optional[str] = None
    confirm_balanced_entry: bool = False
    confirm_document_reviewed: bool = False


class AccountingRejectionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    comment: Optional[str] = None


class AccountingProposalListItem(BaseModel):
    proposal_id: str
    vault_document_id: str
    document_type: str
    document_number: Optional[str] = None
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    amount_ttc: Optional[float] = None
    currency: str = "EUR"
    status: str
    confidence: Optional[float] = None
    requires_review: bool = False
    created_at: datetime
    updated_at: datetime


class AccountingEntryLineView(BaseModel):
    line_id: str
    line_number: int
    account_code: str
    account_label: Optional[str] = None
    third_party_name: Optional[str] = None
    debit: float
    credit: float
    vat_rate: Optional[float] = None
    description: Optional[str] = None


class AccountingEntryView(BaseModel):
    entry_id: str
    journal_code: str
    entry_date: date
    reference: Optional[str] = None
    description: str
    currency: str
    total_debit: float
    total_credit: float
    balanced: bool
    status: str
    lines: list[AccountingEntryLineView] = Field(default_factory=list)


class AccountingReviewView(BaseModel):
    review_id: str
    action: str
    comment: Optional[str] = None
    user_id: int
    created_at: datetime


class AccountingProposalDetail(BaseModel):
    proposal_id: str
    vault_document_id: str
    document_analysis_id: Optional[str] = None
    document_version: int
    document_type: str
    document_number: Optional[str] = None
    document_date: Optional[date] = None
    due_date: Optional[date] = None
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    currency: str
    amount_ht: Optional[float] = None
    amount_vat: Optional[float] = None
    amount_ttc: Optional[float] = None
    status: str
    current_stage: str
    confidence: Optional[float] = None
    requires_review: bool
    review_reasons: list[str] = Field(default_factory=list)
    document_validation: dict[str, Any] = Field(default_factory=dict)
    financial_validation: dict[str, Any] = Field(default_factory=dict)
    accounting_mapping: dict[str, Any] = Field(default_factory=dict)
    quality_summary: dict[str, Any] = Field(default_factory=dict)
    entry: Optional[AccountingEntryView] = None
    reviews: list[AccountingReviewView] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    disclaimer: str = "Proposition générée par ELFIS IA — vérification humaine requise"
    created_at: datetime
    updated_at: datetime
    validated_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None


class BuildProposalAccepted(BaseModel):
    proposal_id: Optional[str] = None
    job_id: Optional[str] = None
    status: str
    reused_existing: bool = False
