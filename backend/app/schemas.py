from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AccountingLine(BaseModel):
    account: str
    label: str
    debit: float = 0.0
    credit: float = 0.0


class AccountingEntry(BaseModel):
    journal: str = "ACH"
    journal_lib: str = "Achats"
    label: str
    piece_ref: str = ""
    piece_date: str = ""  # AAAAMMJJ pour FEC
    lines: list[AccountingLine]
    explanation: str = ""
    imputation: str = ""


class LineItemExtraction(BaseModel):
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


class ExtractionResult(BaseModel):
    supplier: str | None = None
    invoice_date: str | None = None
    invoice_number: str | None = None
    amount_ht: float | None = None
    amount_tva: float | None = None
    amount_ttc: float | None = None
    vat_rate: float | None = None
    document_type: str = "facture"
    confidence_score: float = 0.0
    raw_text: str = ""
    # Champs optionnels enrichis (ELFIS AI) — n'impactent pas le pipeline historique
    supplier_address: str | None = None
    supplier_siret: str | None = None
    supplier_siren: str | None = None
    supplier_vat: str | None = None
    supplier_email: str | None = None
    supplier_phone: str | None = None
    supplier_iban: str | None = None
    supplier_bic: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    customer_siret: str | None = None
    customer_vat: str | None = None
    due_date: str | None = None
    currency: str | None = "EUR"
    payment_terms: str | None = None
    payment_method: str | None = None
    order_reference: str | None = None
    line_items: list[LineItemExtraction] = Field(default_factory=list)
    late_penalty_mention: str | None = None
    recovery_indemnity_mention: str | None = None
    vat_exemption_mention: str | None = None
    reverse_charge_mention: str | None = None


class ValidationResult(BaseModel):
    is_valid: bool = True
    needs_review: bool = False
    anomalies: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    corrected: ExtractionResult | None = None


class InvoiceUpdate(BaseModel):
    supplier: str | None = None
    invoice_date: str | None = None
    invoice_number: str | None = None
    amount_ht: float | None = None
    amount_tva: float | None = None
    amount_ttc: float | None = None
    vat_rate: float | None = None
    document_type: str | None = None
    status: str | None = None
    needs_review: bool | None = None


class InvoiceOut(BaseModel):
    id: int
    filename: str
    mime_type: str | None = None
    supplier: str | None
    invoice_date: str | None
    invoice_number: str | None
    amount_ht: float | None
    amount_tva: float | None
    amount_ttc: float | None
    vat_rate: float | None
    document_type: str | None
    confidence_score: float | None
    status: str
    needs_review: bool
    anomalies: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    accounting_entry: AccountingEntry | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    invoice_count: int
    total_ht: float
    recoverable_vat: float
    to_review: int
    recent: list[InvoiceOut]


class CompanySettingsIn(BaseModel):
    company_name: str = "Mon Entreprise"
    siret: str = ""
    vat_number: str = ""
    default_vat_rate: float = 20.0
    expense_account: str = "606"
    vat_account: str = "44566"
    supplier_account: str = "401"
    accountant_firm: str = ""
    accountant_email: str = ""
    confidence_threshold: float = 0.85


class CompanySettingsOut(CompanySettingsIn):
    id: int

    model_config = {"from_attributes": True}


class HealthOut(BaseModel):
    status: str
    app: str
    product: str
    ai_mode: str
    details: dict[str, Any] = Field(default_factory=dict)