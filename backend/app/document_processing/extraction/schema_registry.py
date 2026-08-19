"""Registre de schémas d'extraction — définis en code uniquement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.document_processing.extraction.exceptions import ExtractionValidationError
from app.document_processing.extraction.types import (
    SCHEMA_GENERIC_V1,
    SCHEMA_INVOICE_BASIC_V1,
    SCHEMA_QUOTE_BASIC_V1,
    SCHEMA_RECEIPT_BASIC_V1,
    FieldType,
)


@dataclass(frozen=True)
class ExtractionFieldDef:
    path: str
    field_type: FieldType
    required: bool = False
    sensitive: bool = False
    max_length: int = 500
    enum_values: frozenset[str] | None = None
    nested: tuple["ExtractionFieldDef", ...] = ()


@dataclass(frozen=True)
class ExtractionSchemaDef:
    schema_key: str
    schema_version: str
    supported_document_types: frozenset[str]
    fields: tuple[ExtractionFieldDef, ...]
    human_review_mandatory: bool = False
    description: str = ""

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(f.path for f in self.fields if f.required)

    @property
    def optional_fields(self) -> tuple[str, ...]:
        return tuple(f.path for f in self.fields if not f.required)

    def field_map(self) -> dict[str, ExtractionFieldDef]:
        return {f.path: f for f in self.fields}

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_key": self.schema_key,
            "schema_version": self.schema_version,
            "supported_document_types": sorted(self.supported_document_types),
            "required_fields": list(self.required_fields),
            "optional_fields": list(self.optional_fields),
            "fields": [
                {
                    "path": f.path,
                    "type": f.field_type.value,
                    "required": f.required,
                    "sensitive": f.sensitive,
                    "max_length": f.max_length,
                }
                for f in self.fields
            ],
            "human_review_mandatory": self.human_review_mandatory,
            "description": self.description,
        }


def _f(
    path: str,
    ftype: FieldType,
    *,
    required: bool = False,
    sensitive: bool = False,
    max_length: int = 500,
) -> ExtractionFieldDef:
    return ExtractionFieldDef(
        path=path,
        field_type=ftype,
        required=required,
        sensitive=sensitive,
        max_length=max_length,
    )


GENERIC_DOCUMENT_V1 = ExtractionSchemaDef(
    schema_key=SCHEMA_GENERIC_V1,
    schema_version="1",
    supported_document_types=frozenset({"unknown", "supporting_document", "contract", "tax_document"}),
    human_review_mandatory=False,
    description="Métadonnées documentaires génériques ELFIS",
    fields=(
        _f("title", FieldType.STRING, max_length=300),
        _f("document_date", FieldType.DATE),
        _f("reference", FieldType.STRING, max_length=120),
        _f("parties", FieldType.STRING, max_length=500),
        _f("detected_language", FieldType.STRING, max_length=16),
        _f("summary_metadata", FieldType.STRING, max_length=500),
    ),
)

INVOICE_BASIC_V1 = ExtractionSchemaDef(
    schema_key=SCHEMA_INVOICE_BASIC_V1,
    schema_version="1",
    supported_document_types=frozenset(
        {"invoice", "supplier_invoice", "customer_invoice", "credit_note"}
    ),
    human_review_mandatory=True,
    description="Structure facture générique — aucun mapping comptable",
    fields=(
        _f("invoice_number", FieldType.STRING, required=True, max_length=120),
        _f("issue_date", FieldType.DATE, required=True),
        _f("due_date", FieldType.DATE),
        _f("supplier_name", FieldType.STRING, required=True, sensitive=True, max_length=300),
        _f("customer_name", FieldType.STRING, sensitive=True, max_length=300),
        _f("currency", FieldType.CURRENCY_CODE, required=True),
        _f("subtotal", FieldType.DECIMAL),
        _f("tax_amount", FieldType.DECIMAL),
        _f("total_amount", FieldType.DECIMAL, required=True),
        _f("tax_rate", FieldType.PERCENTAGE),
        _f("payment_terms", FieldType.STRING, max_length=200),
        _f("purchase_order_reference", FieldType.STRING, max_length=120),
    ),
)

QUOTE_BASIC_V1 = ExtractionSchemaDef(
    schema_key=SCHEMA_QUOTE_BASIC_V1,
    schema_version="1",
    supported_document_types=frozenset({"quote"}),
    human_review_mandatory=True,
    description="Structure devis générique",
    fields=(
        _f("quote_number", FieldType.STRING, required=True, max_length=120),
        _f("issue_date", FieldType.DATE, required=True),
        _f("validity_date", FieldType.DATE),
        _f("issuer_name", FieldType.STRING, required=True, sensitive=True, max_length=300),
        _f("customer_name", FieldType.STRING, sensitive=True, max_length=300),
        _f("currency", FieldType.CURRENCY_CODE, required=True),
        _f("subtotal", FieldType.DECIMAL),
        _f("tax_amount", FieldType.DECIMAL),
        _f("total_amount", FieldType.DECIMAL, required=True),
    ),
)

RECEIPT_BASIC_V1 = ExtractionSchemaDef(
    schema_key=SCHEMA_RECEIPT_BASIC_V1,
    schema_version="1",
    supported_document_types=frozenset({"receipt", "expense_report"}),
    human_review_mandatory=True,
    description="Structure ticket / reçu générique",
    fields=(
        _f("merchant_name", FieldType.STRING, required=True, sensitive=True, max_length=300),
        _f("transaction_date", FieldType.DATE, required=True),
        _f("total_amount", FieldType.DECIMAL, required=True),
        _f("tax_amount", FieldType.DECIMAL),
        _f("currency", FieldType.CURRENCY_CODE),
        _f("payment_method", FieldType.STRING, max_length=80),
    ),
)


class DocumentExtractionSchemaRegistry:
    def __init__(self) -> None:
        self._schemas: dict[tuple[str, str], ExtractionSchemaDef] = {}
        for s in (GENERIC_DOCUMENT_V1, INVOICE_BASIC_V1, QUOTE_BASIC_V1, RECEIPT_BASIC_V1):
            self.register(s)

    def register(self, schema: ExtractionSchemaDef) -> None:
        self._schemas[(schema.schema_key, schema.schema_version)] = schema

    def get(self, schema_key: str, schema_version: str = "1") -> ExtractionSchemaDef:
        s = self._schemas.get((schema_key, schema_version))
        if not s:
            raise ExtractionValidationError("schema_unknown", f"Schéma inconnu: {schema_key}@{schema_version}")
        return s

    def latest(self, schema_key: str) -> ExtractionSchemaDef:
        matches = [s for (k, _), s in self._schemas.items() if k == schema_key]
        if not matches:
            raise ExtractionValidationError("schema_unknown", f"Schéma inconnu: {schema_key}")
        return sorted(matches, key=lambda x: x.schema_version, reverse=True)[0]

    def list_public(self) -> list[dict[str, Any]]:
        return [s.to_public_dict() for s in sorted(self._schemas.values(), key=lambda x: x.schema_key)]

    def for_document_type(self, document_type: str | None) -> ExtractionSchemaDef | None:
        if not document_type:
            return None
        for s in self._schemas.values():
            if document_type in s.supported_document_types:
                return s
        return None


_REGISTRY: DocumentExtractionSchemaRegistry | None = None


def get_extraction_schema_registry() -> DocumentExtractionSchemaRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DocumentExtractionSchemaRegistry()
    return _REGISTRY


def reset_extraction_schema_registry_for_tests() -> None:
    global _REGISTRY
    _REGISTRY = None
