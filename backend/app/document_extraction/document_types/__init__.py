"""Schémas d'extraction versionnés par type de document."""

from __future__ import annotations

from typing import Any

SCHEMA_REGISTRY: dict[str, dict[str, Any]] = {}


def _reg(schema: dict[str, Any]) -> dict[str, Any]:
    SCHEMA_REGISTRY[schema["schema_name"]] = schema
    return schema


INVOICE_V1 = _reg(
    {
        "schema_name": "invoice.v1",
        "schema_version": "1.0.0",
        "document_type": "invoice",
        "critical_fields": [
            "document_number",
            "document_date",
            "supplier.name",
            "amounts.total_including_tax",
            "amounts.total_tax",
            "currency",
        ],
        "recommended_fields": [
            "due_date",
            "customer.name",
            "amounts.subtotal_excluding_tax",
            "supplier.vat_number",
        ],
        "optional_fields": [
            "supplier.iban",
            "payment.payment_terms",
            "line_items",
            "taxes",
            "metadata.notes",
        ],
        "field_types": {
            "document_number": "string",
            "document_date": "date",
            "due_date": "date",
            "currency": "currency",
            "amounts.total_including_tax": "decimal",
            "amounts.subtotal_excluding_tax": "decimal",
            "amounts.total_tax": "decimal",
        },
    }
)

QUOTE_V1 = _reg(
    {
        "schema_name": "quote.v1",
        "schema_version": "1.0.0",
        "document_type": "quote",
        "critical_fields": ["quote_number", "issue_date", "supplier.name", "amounts.total_including_tax"],
        "recommended_fields": ["validity_date", "customer.name", "currency"],
        "optional_fields": ["line_items", "payment_terms", "notes"],
        "field_types": {},
    }
)

CREDIT_NOTE_V1 = _reg(
    {
        "schema_name": "credit_note.v1",
        "schema_version": "1.0.0",
        "document_type": "credit_note",
        "critical_fields": [
            "credit_note_number",
            "credit_note_date",
            "supplier.name",
            "amounts.total_including_tax",
        ],
        "recommended_fields": ["original_invoice_number", "reason", "customer.name"],
        "optional_fields": ["line_items", "taxes"],
        "field_types": {},
    }
)

RECEIPT_V1 = _reg(
    {
        "schema_name": "receipt.v1",
        "schema_version": "1.0.0",
        "document_type": "receipt",
        "critical_fields": ["merchant_name", "document_date", "total_including_tax"],
        "recommended_fields": ["currency", "payment_method"],
        "optional_fields": ["line_items", "taxes", "receipt_number"],
        "field_types": {},
    }
)

BANK_STATEMENT_V1 = _reg(
    {
        "schema_name": "bank_statement.v1",
        "schema_version": "1.0.0",
        "document_type": "bank_statement",
        "critical_fields": [
            "statement_period_start",
            "statement_period_end",
            "opening_balance",
            "closing_balance",
            "currency",
        ],
        "recommended_fields": ["bank_name", "iban_masked", "transactions"],
        "optional_fields": ["account_holder", "bic"],
        "field_types": {},
    }
)

CONTRACT_V1 = _reg(
    {
        "schema_name": "contract.v1",
        "schema_version": "1.0.0",
        "document_type": "contract",
        "critical_fields": ["contract_title", "parties"],
        "recommended_fields": ["effective_date", "end_date", "governing_law"],
        "optional_fields": ["key_clauses", "signatories", "total_value"],
        "field_types": {},
    }
)

GENERIC_V1 = _reg(
    {
        "schema_name": "generic_document.v1",
        "schema_version": "1.0.0",
        "document_type": "generic_document",
        "critical_fields": [],
        "recommended_fields": ["title", "document_date", "summary"],
        "optional_fields": ["parties", "amounts", "references"],
        "field_types": {},
    }
)

DOC_TYPE_TO_SCHEMA = {
    "invoice": "invoice.v1",
    "quote": "quote.v1",
    "credit_note": "credit_note.v1",
    "receipt": "receipt.v1",
    "bank_statement": "bank_statement.v1",
    "contract": "contract.v1",
    "unknown": "generic_document.v1",
    "generic_document": "generic_document.v1",
}


def get_schema(name: str | None, document_type: str | None = None) -> dict[str, Any]:
    if name and name in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[name]
    mapped = DOC_TYPE_TO_SCHEMA.get(document_type or "unknown", "generic_document.v1")
    return SCHEMA_REGISTRY[mapped]
