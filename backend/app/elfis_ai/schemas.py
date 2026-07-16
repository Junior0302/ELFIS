from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ANALYSIS_VERSION = "1.0.0"
NOT_AVAILABLE = "not_available"
INSUFFICIENT_DATA = "insufficient_data"

FieldStatus = Literal["found", "uncertain", "missing", "not_available"]
Severity = Literal["information", "faible", "moyenne", "elevee", "critique"]
ComplianceStatus = Literal["conforme", "manquant", "incertain", "non_applicable"]
Certainty = Literal["certain", "probable", "multiple", "review_required"]


class FieldValue(BaseModel):
    value: Any = None
    confidence: float = 0.0
    source: str = "extraction"
    status: FieldStatus = "not_available"
    anomaly: str | None = None


class LineItemReport(BaseModel):
    label: str | None = None
    description: str | None = None
    reference: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price_ht: float | None = None
    discount: float | None = None
    vat_rate: float | None = None
    vat_amount: float | None = None
    total_ht: float | None = None
    total_ttc: float | None = None


class ExtractionBlock(BaseModel):
    supplier: dict[str, FieldValue] = Field(default_factory=dict)
    customer: dict[str, FieldValue] = Field(default_factory=dict)
    document: dict[str, FieldValue] = Field(default_factory=dict)
    line_items: list[LineItemReport] = Field(default_factory=list)
    totals: dict[str, FieldValue] = Field(default_factory=dict)
    legal_mentions: dict[str, FieldValue] = Field(default_factory=dict)


class ConfidenceFactor(BaseModel):
    label: str
    positive: bool = True
    detail: str = ""


class ConfidenceBlock(BaseModel):
    global_score: float = 0.0
    factors: list[ConfidenceFactor] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    uncertain_fields: list[str] = Field(default_factory=list)
    summary: str = ""


class AccountingLineExplain(BaseModel):
    account: str
    label: str
    debit: float = 0.0
    credit: float = 0.0
    justification: str = ""
    certainty: Certainty = "probable"


class AccountingBlock(BaseModel):
    journal: str = "ACH"
    entry_date: str | None = None
    label: str = ""
    currency: str = "EUR"
    lines: list[AccountingLineExplain] = Field(default_factory=list)
    total_debit: float = 0.0
    total_credit: float = 0.0
    balanced: bool = False
    confidence: float = 0.0
    review_required: bool = False
    potential_immobilization: bool = False
    explanations: list[str] = Field(default_factory=list)
    status: str = "ok"


class AnomalyItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    severity: Severity = "moyenne"
    field: str | None = None
    detected_value: Any = None
    expected_value: Any = None
    recommended_action: str = ""
    blocking: bool = False


class ChecksBlock(BaseModel):
    calculation_checks: list[AnomalyItem] = Field(default_factory=list)
    tax_checks: list[AnomalyItem] = Field(default_factory=list)
    compliance_checks: list[AnomalyItem] = Field(default_factory=list)
    anomalies: list[AnomalyItem] = Field(default_factory=list)


class FinancialBlock(BaseModel):
    status: str = "ok"
    monthly_weight_pct: float | None = None
    cash_impact: str | None = None
    recommended_payment_date: str | None = None
    amount_remaining: float | None = None
    due_in_days: int | None = None
    supplier_avg_amount: float | None = None
    vs_supplier_avg_pct: float | None = None
    unusual_amount: bool | None = None
    messages: list[str] = Field(default_factory=list)
    limitations: str = ""


class RiskFactor(BaseModel):
    code: str
    label: str
    detail: str = ""


class RiskBlock(BaseModel):
    score: float = 0.0
    level: Literal["faible", "modere", "eleve", "critique"] = "faible"
    factors: list[RiskFactor] = Field(default_factory=list)
    explanation: str = ""
    recommendation: str = "Aucune anomalie significative détectée."
    never_assert_fraud: bool = True


class TaxBlock(BaseModel):
    recoverable_vat: float | None = None
    vat_rate: float | None = None
    exemption: bool | None = None
    reverse_charge: bool | None = None
    deductible_expense: str = "indicative"
    potential_immobilization: bool = False
    messages: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Cette analyse est indicative et doit être validée selon la situation fiscale "
        "réelle de l'entreprise."
    )


class ComplianceItem(BaseModel):
    code: str
    label: str
    status: ComplianceStatus = "incertain"
    detail: str = ""


class ComplianceBlock(BaseModel):
    items: list[ComplianceItem] = Field(default_factory=list)
    synthesis: Literal["elevee", "partielle", "verification_necessaire"] = "partielle"
    summary: str = ""


class SupplierBlock(BaseModel):
    status: str = INSUFFICIENT_DATA
    known_supplier: bool | None = None
    document_count: int = 0
    last_document_date: str | None = None
    average_amount: float | None = None
    cumulative_amount: float | None = None
    purchase_frequency: str | None = None
    price_trend: str | None = None
    iban_history: list[str] = Field(default_factory=list)
    previous_anomalies: int = 0
    messages: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    category: str
    priority: Literal["basse", "moyenne", "haute", "urgente"] = "moyenne"
    title: str
    description: str
    action: str = ""
    reason: str = ""
    status: str = "open"


class CfoSummary(BaseModel):
    what_is_it: str = ""
    is_coherent: str = ""
    main_impact: str = ""
    next_action: str = ""
    summary: str = ""
    limitations: list[str] = Field(default_factory=list)


class AnalysisMetadata(BaseModel):
    analysis_id: int | None = None
    document_id: int
    organization_id: int
    user_id: int | None = None
    analysis_version: str = ANALYSIS_VERSION
    processing_time_ms: int = 0
    status: str = "completed"
    created_at: str | None = None
    updated_at: str | None = None


class ElfisReport(BaseModel):
    metadata: AnalysisMetadata
    extraction: ExtractionBlock = Field(default_factory=ExtractionBlock)
    confidence: ConfidenceBlock = Field(default_factory=ConfidenceBlock)
    accounting: AccountingBlock = Field(default_factory=AccountingBlock)
    checks: ChecksBlock = Field(default_factory=ChecksBlock)
    financial_analysis: FinancialBlock = Field(default_factory=FinancialBlock)
    risk_analysis: RiskBlock = Field(default_factory=RiskBlock)
    tax_analysis: TaxBlock = Field(default_factory=TaxBlock)
    compliance: ComplianceBlock = Field(default_factory=ComplianceBlock)
    supplier_intelligence: SupplierBlock = Field(default_factory=SupplierBlock)
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    cfo_summary: CfoSummary = Field(default_factory=CfoSummary)
    summary_card: dict[str, Any] = Field(default_factory=dict)
