"""Contexte et résultats d'exécution de règles."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol


@dataclass
class ValidationIssueDraft:
    rule_key: str
    rule_version: str
    severity: str
    issue_code: str
    field_paths: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    blocking: bool = False
    message_code: str | None = None


@dataclass
class RuleContext:
    schema_key: str
    document_type: str | None
    fields: dict[str, Any]  # normalized values from extraction artifact
    amount_tolerance: Decimal
    percentage_tolerance: Decimal
    extraction_status: str | None = None
    extraction_requires_review: bool = False
    classification_ambiguous: bool = False


class BusinessValidationRule(Protocol):
    rule_key: str
    rule_version: str
    supported_schemas: frozenset[str]
    severity: str
    blocking: bool

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]: ...
