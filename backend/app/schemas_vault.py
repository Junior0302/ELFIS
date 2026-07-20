"""Schémas Pydantic pour ELFIS Vault."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VaultDocumentType(str, Enum):
    customer_invoice = "customer_invoice"
    supplier_invoice = "supplier_invoice"
    quote = "quote"
    credit_note = "credit_note"
    expense_report = "expense_report"
    bank_statement = "bank_statement"
    contract = "contract"
    other = "other"


class VaultArchiveStatus(str, Enum):
    archived = "archived"
    deleted = "deleted"
    pending = "pending"


class VaultEmailStatus(str, Enum):
    not_sent = "not_sent"
    sent = "sent"
    failed = "failed"


class VaultAccountingStatus(str, Enum):
    not_processed = "not_processed"
    processed = "processed"
    exported = "exported"


class VaultActivityAction(str, Enum):
    document_archived = "document_archived"
    document_deleted = "document_deleted"
    document_downloaded = "document_downloaded"


DOCUMENT_TYPE_CATEGORIES: dict[VaultDocumentType, str] = {
    VaultDocumentType.customer_invoice: "factures-clients",
    VaultDocumentType.supplier_invoice: "factures-fournisseurs",
    VaultDocumentType.quote: "devis",
    VaultDocumentType.credit_note: "avoirs",
    VaultDocumentType.expense_report: "notes-de-frais",
    VaultDocumentType.bank_statement: "releves-bancaires",
    VaultDocumentType.contract: "contrats",
    VaultDocumentType.other: "autres",
}


class VaultArchiveFormMeta(BaseModel):
    """Métadonnées d'archivage (hors fichier)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tenant_id: int = Field(..., ge=1, description="organization_id ComptaPilot")
    document_type: VaultDocumentType
    document_number: str | None = Field(default=None, max_length=128)
    invoice_date: date | None = None
    due_date: date | None = None
    amount_ht: Decimal | None = None
    amount_vat: Decimal | None = None
    amount_ttc: Decimal | None = None
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    customer_id: int | None = None
    supplier_id: int | None = None

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, value: str) -> str:
        cleaned = (value or "EUR").strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("La devise doit contenir exactement 3 lettres")
        return cleaned

    @field_validator("amount_ht", "amount_vat", "amount_ttc")
    @classmethod
    def amounts_non_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("Les montants ne peuvent pas être négatifs")
        return value

    @field_validator("document_number")
    @classmethod
    def empty_number_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class VaultDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: int
    document_type: VaultDocumentType
    document_number: str | None = None
    original_filename: str
    storage_path: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    archive_status: VaultArchiveStatus
    accounting_status: VaultAccountingStatus
    email_status: VaultEmailStatus
    version: int
    archived_at: datetime
    created_at: datetime


class VaultDuplicateErrorBody(BaseModel):
    detail: str
    existing_document_id: str


class VaultActivityLogCreate(BaseModel):
    organization_id: int
    document_id: str
    user_id: int | None
    action: VaultActivityAction
    metadata: dict[str, Any] = Field(default_factory=dict)
