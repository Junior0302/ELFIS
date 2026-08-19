"""Enums Migration Memory."""

from __future__ import annotations

from enum import Enum


class MemoryScope(str, Enum):
    SESSION = "session"
    ORGANIZATION = "organization"
    PRODUCT = "product"


# Seul scope autorisé en écriture pour cette passe
WRITABLE_SCOPES = frozenset({MemoryScope.SESSION.value})


class MemoryStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MemorySource(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AI = "ai"
    IMPORT_RULE = "import_rule"


class MemoryType(str, Enum):
    SUPPLIER_CLASSIFICATION = "supplier_classification"
    CUSTOMER_MATCH = "customer_match"
    FIELD_MAPPING = "field_mapping"
    DUPLICATE_RESOLUTION = "duplicate_resolution"
    DOCUMENT_TYPE = "document_type"
    TAX_RULE = "tax_rule"
    ACCOUNTING_MAPPING = "accounting_mapping"
    IMPORT_PREFERENCE = "import_preference"
