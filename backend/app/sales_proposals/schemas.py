"""Commercial Proposal Engine V1 — Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.sales_proposals.enums import (
    AmountOverrideReason,
    DiscountType,
    ProposalType,
)

# ----- Write models -----


class ProposalCreate(BaseModel):
    opportunity_id: int | None = None
    sales_company_id: int | None = None
    person_id: int | None = None
    proposal_type: ProposalType = ProposalType.quote
    title: str = Field(default="Proposition commerciale", max_length=255)
    currency: str = Field(default="EUR", max_length=8)
    valid_until: date | None = None
    seed_from_opportunity_products: bool = True
    amount_source: Literal["calculated", "final"] = "final"


class ProposalUpdate(BaseModel):
    """Champs modifiables tant que la version courante n'est pas verrouillée.

    Les champs `sales_company_id`/`person_id`/`owner_user_id`/`currency`/`valid_until`
    vivent sur la proposition ; les autres vivent sur la version courante.
    """

    sales_company_id: int | None = None
    person_id: int | None = None
    owner_user_id: int | None = None
    currency: str | None = Field(default=None, max_length=8)
    valid_until: date | None = None
    title: str | None = Field(default=None, max_length=255)
    introduction: str | None = None
    scope: str | None = None
    terms: str | None = None
    payment_terms: str | None = None
    notes: str | None = None
    expected_updated_at: datetime | None = None


class LineCreate(BaseModel):
    catalog_item_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    quantity: Decimal = Field(default=Decimal("1"))
    unit_price: Decimal = Field(default=Decimal("0"))
    discount_type: DiscountType = DiscountType.none
    discount_value: Decimal = Field(default=Decimal("0"))
    tax_rate: Decimal = Field(default=Decimal("20"))
    position: int | None = None
    expected_updated_at: datetime | None = None


class LineUpdate(BaseModel):
    catalog_item_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = None
    tax_rate: Decimal | None = None
    position: int | None = None
    expected_updated_at: datetime | None = None


class AcceptIn(BaseModel):
    comment: str | None = None


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=255)
    comment: str | None = None


class AmountOverrideIn(BaseModel):
    reason: AmountOverrideReason
    comment: str | None = None


# ----- Read models -----


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    opportunity_id: int | None = None
    sales_company_id: int | None = None
    person_id: int | None = None
    proposal_number: str
    proposal_type: str
    status: str
    current_version_id: int | None = None
    owner_user_id: int | None = None
    currency: str
    valid_until: date | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    expired_at: datetime | None = None
    converted_at: datetime | None = None
    linked_customer_id: int | None = None
    linked_invoice_id: int | None = None
    reject_reason: str | None = None
    reject_comment: str | None = None
    created_at: datetime
    updated_at: datetime


class LineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proposal_version_id: int
    catalog_item_id: int | None = None
    source_opportunity_product_id: int | None = None
    position: int
    name: str
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    discount_type: str
    discount_value: Decimal
    tax_rate: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proposal_id: int
    version_number: int
    status: str
    title: str
    introduction: str | None = None
    scope: str | None = None
    terms: str | None = None
    payment_terms: str | None = None
    notes: str | None = None
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    currency: str
    valid_until: date | None = None
    readiness_score: int
    readiness_level: str
    readiness_explanation: dict[str, Any] = Field(default_factory=dict)
    pdf_vault_document_id: Any | None = None
    checksum: str | None = None
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None = None
    viewed_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    locked_at: datetime | None = None
    lines: list[LineOut] = Field(default_factory=list)


# ----- Workspace -----


class WorkspaceHeaderOut(BaseModel):
    proposal_id: int
    proposal_number: str
    proposal_type: str
    status: str
    title: str
    currency: str
    valid_until: date | None = None
    owner_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    company_name: str | None = None
    opportunity_id: int | None = None
    opportunity_name: str | None = None
    version_number: int | None = None
    total: Decimal | None = None


class VersionSummaryOut(BaseModel):
    id: int
    version_number: int
    status: str
    total: Decimal
    created_at: datetime
    is_current: bool = False


class WorkspaceTotalsOut(BaseModel):
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    currency: str


class WorkspaceReadinessOut(BaseModel):
    score: int
    level: str
    checks: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class WorkspaceWorkflowOut(BaseModel):
    status: str
    version_status: str
    locked: bool
    allowed_transitions: list[str] = Field(default_factory=list)


class WorkspaceCompanyOut(BaseModel):
    id: int | None = None
    name: str | None = None
    siret: str | None = None
    vat_number: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None


class WorkspaceContactOut(BaseModel):
    id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None


class WorkspaceOpportunityOut(BaseModel):
    id: int | None = None
    name: str | None = None
    status: str | None = None
    amount: Decimal | None = None


class WorkspaceDocumentOut(BaseModel):
    version_id: int
    version_number: int
    vault_document_id: str | None = None
    checksum: str | None = None
    generated: bool = False
    generated_at: datetime | None = None
    open_url: str | None = None
    label: str | None = None


class WorkspaceTimelineItemOut(BaseModel):
    id: int
    event_type: str
    title: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionOut(BaseModel):
    id: str
    label: str
    kind: str = "action"
    enabled: bool = True
    reason: str | None = None
    disabled_reason: str | None = None
    permission: str | None = None
    requires_confirmation: bool = False
    destructive: bool = False
    expected_result: str | None = None


class WorkspaceConversionStateOut(BaseModel):
    can_convert: bool = False
    linked_customer_id: int | None = None
    linked_invoice_id: int | None = None
    conversion_status: str | None = None
    reasons: list[str] = Field(default_factory=list)


class WorkspaceOut(BaseModel):
    header: WorkspaceHeaderOut
    current_version: VersionOut | None = None
    versions: list[VersionSummaryOut] = Field(default_factory=list)
    lines: list[LineOut] = Field(default_factory=list)
    totals: WorkspaceTotalsOut
    readiness: WorkspaceReadinessOut
    workflow: WorkspaceWorkflowOut
    company: WorkspaceCompanyOut | None = None
    contact: WorkspaceContactOut | None = None
    opportunity: WorkspaceOpportunityOut | None = None
    documents: list[WorkspaceDocumentOut] = Field(default_factory=list)
    timeline: list[WorkspaceTimelineItemOut] = Field(default_factory=list)
    available_actions: list[ActionOut] = Field(default_factory=list)
    conversion_state: WorkspaceConversionStateOut
    generated_at: datetime


class DiffOut(BaseModel):
    from_version: int | None = None
    to_version: int | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    changes: dict[str, Any] = Field(default_factory=dict)


class ConversionPreviewOut(BaseModel):
    linked_customer: dict[str, Any] | None = None
    duplicate_candidates: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    conversion_preview: dict[str, Any] = Field(default_factory=dict)
    available_actions: list[ActionOut] = Field(default_factory=list)


class ConversionCustomerIn(BaseModel):
    customer_resolution_mode: Literal[
        "use_linked_customer", "use_existing_customer", "create_new_customer"
    ]
    customer_id: int | None = None
    customer_payload: dict[str, Any] | None = None
    confirm_possible_match: bool = False
    force_create: bool = False


class ConvertToInvoiceIn(BaseModel):
    customer_resolution_mode: Literal[
        "use_linked_customer", "use_existing_customer", "create_new_customer"
    ]
    customer_id: int | None = None
    customer_payload: dict[str, Any] | None = None
    accepted_version_id: int | None = None
    expected_proposal_updated_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)
    confirm_possible_match: bool = False


class ConversionStateOut(BaseModel):
    proposal_id: int
    proposal_status: str
    accepted_version_id: int | None = None
    conversion_status: str
    linked_customer_id: int | None = None
    linked_invoice_id: int | None = None
    customer_resolution: dict[str, Any] = Field(default_factory=dict)
    duplicate_candidates: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    preview_available: bool = False
    can_convert: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime


class InvoiceConversionPreviewOut(BaseModel):
    proposal: dict[str, Any]
    accepted_version: dict[str, Any]
    customer: dict[str, Any] | None = None
    invoice_header: dict[str, Any]
    invoice_lines: list[dict[str, Any]] = Field(default_factory=list)
    subtotal: str
    discount_total: str
    tax_total: str
    total: str
    currency: str
    payment_terms: str | None = None
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    multi_vat_rates: list[float] = Field(default_factory=list)
    source_mapping: dict[str, Any] = Field(default_factory=dict)
    can_confirm: bool = False
    linked_invoice_id: int | None = None


class ConvertToInvoiceOut(BaseModel):
    already_converted: bool = False
    proposal_id: int
    invoice_id: int
    invoice_number: str
    invoice_status: str
    customer_id: int | None = None
    message: str | None = None
