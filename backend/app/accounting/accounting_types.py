"""Types Accounting Pipeline V1."""

from __future__ import annotations


class AccountingDocumentTypes:
    SUPPLIER_INVOICE = "supplier_invoice"
    CUSTOMER_INVOICE = "customer_invoice"
    CREDIT_NOTE = "credit_note"
    QUOTE = "quote"
    EXPENSE_REPORT = "expense_report"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    OTHER = "other"


SUPPORTED_DOCUMENT_TYPES_V1: frozenset[str] = frozenset(
    {
        AccountingDocumentTypes.SUPPLIER_INVOICE,
        AccountingDocumentTypes.CUSTOMER_INVOICE,
        AccountingDocumentTypes.CREDIT_NOTE,
    }
)

PREPARED_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        AccountingDocumentTypes.QUOTE,
        AccountingDocumentTypes.EXPENSE_REPORT,
        AccountingDocumentTypes.RECEIPT,
        AccountingDocumentTypes.BANK_STATEMENT,
    }
)


class ProposalStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    VALIDATION_FAILED = "validation_failed"
    FINANCIAL_ERROR = "financial_error"
    MAPPING_FAILED = "mapping_failed"
    REQUIRES_REVIEW = "requires_review"
    READY_FOR_VALIDATION = "ready_for_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProposalStage:
    INITIALIZATION = "initialization"
    DOCUMENT_VALIDATION = "document_validation"
    FINANCIAL_VALIDATION = "financial_validation"
    ACCOUNTING_MAPPING = "accounting_mapping"
    REVIEW = "review"
    COMPLETED = "completed"


class EntryStatus:
    DRAFT = "draft"
    PROPOSED = "proposed"
    VALIDATED = "validated"
    EXPORTED = "exported"
    CANCELLED = "cancelled"


class ReviewAction:
    CREATED = "created"
    EDITED = "edited"
    VALIDATED = "validated"
    REJECTED = "rejected"
    REOPENED = "reopened"
    MAPPING_CHANGED = "mapping_changed"
    AMOUNTS_CHANGED = "amounts_changed"
    ACCOUNT_CHANGED = "account_changed"


# Mapping AI / historique FR → type pipeline
DOC_TYPE_ALIASES: dict[str, str] = {
    "facture": AccountingDocumentTypes.SUPPLIER_INVOICE,
    "supplier_invoice": AccountingDocumentTypes.SUPPLIER_INVOICE,
    "customer_invoice": AccountingDocumentTypes.CUSTOMER_INVOICE,
    "avoir": AccountingDocumentTypes.CREDIT_NOTE,
    "credit_note": AccountingDocumentTypes.CREDIT_NOTE,
    "devis": AccountingDocumentTypes.QUOTE,
    "quote": AccountingDocumentTypes.QUOTE,
    "ticket": AccountingDocumentTypes.RECEIPT,
    "receipt": AccountingDocumentTypes.RECEIPT,
    "note_frais": AccountingDocumentTypes.EXPENSE_REPORT,
    "expense_report": AccountingDocumentTypes.EXPENSE_REPORT,
    "releve": AccountingDocumentTypes.BANK_STATEMENT,
    "bank_statement": AccountingDocumentTypes.BANK_STATEMENT,
    "autre": AccountingDocumentTypes.OTHER,
    "other": AccountingDocumentTypes.OTHER,
}


def normalize_document_type(raw: str | None) -> str:
    key = (raw or "").strip().lower().replace(" ", "_")
    return DOC_TYPE_ALIASES.get(key, AccountingDocumentTypes.OTHER)
