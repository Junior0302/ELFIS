"""Registre rule sets — définis en code uniquement."""

from __future__ import annotations

from dataclasses import dataclass

from app.document_processing.validation.exceptions import BusinessValidationValidationError
from app.document_processing.validation.rule_base import BusinessValidationRule, RuleContext, ValidationIssueDraft
from app.document_processing.validation.rules import (
    AmountNonNegativeRule,
    AmountPositiveRule,
    CurrencyValidRule,
    DueDateAfterIssueRule,
    ExtractionReviewGateRule,
    InvoiceTotalsConsistencyRule,
    RequiredFieldRule,
    TaxNotExceedTotalRule,
    TaxRateRangeRule,
    ValidityDateAfterIssueRule,
)
from app.document_processing.validation.types import (
    RULE_SET_GENERIC_V1,
    RULE_SET_INVOICE_V1,
    RULE_SET_QUOTE_V1,
    RULE_SET_RECEIPT_V1,
)

_INV = frozenset({"invoice_basic_v1"})
_QUO = frozenset({"quote_basic_v1"})
_REC = frozenset({"receipt_basic_v1"})
_GEN = frozenset({"generic_document_v1"})
_ALL_FIN = frozenset({"invoice_basic_v1", "quote_basic_v1", "receipt_basic_v1"})


@dataclass(frozen=True)
class RuleSetDef:
    key: str
    version: str
    schemas: frozenset[str]
    rules: tuple[BusinessValidationRule, ...]


def _invoice_rules() -> tuple[BusinessValidationRule, ...]:
    return (
        RequiredFieldRule("invoice_number_present", "invoice_number", "INVOICE_NUMBER_MISSING", _INV),
        RequiredFieldRule("issue_date_present", "issue_date", "ISSUE_DATE_MISSING", _INV),
        RequiredFieldRule("supplier_name_present", "supplier_name", "SUPPLIER_NAME_MISSING", _INV),
        RequiredFieldRule("currency_present", "currency", "CURRENCY_MISSING", _INV),
        RequiredFieldRule("total_amount_present", "total_amount", "TOTAL_AMOUNT_MISSING", _INV),
        CurrencyValidRule(),
        AmountPositiveRule("total_amount", "TOTAL_AMOUNT_NON_POSITIVE", _INV),
        AmountNonNegativeRule("subtotal", "SUBTOTAL_NEGATIVE", _INV),
        AmountNonNegativeRule("tax_amount", "TAX_AMOUNT_NEGATIVE", _INV),
        TaxRateRangeRule(),
        DueDateAfterIssueRule(),
        InvoiceTotalsConsistencyRule(),
        TaxNotExceedTotalRule(),
        ExtractionReviewGateRule(),
    )


def _quote_rules() -> tuple[BusinessValidationRule, ...]:
    return (
        RequiredFieldRule("quote_number_present", "quote_number", "QUOTE_NUMBER_MISSING", _QUO),
        RequiredFieldRule("issue_date_present", "issue_date", "ISSUE_DATE_MISSING", _QUO),
        RequiredFieldRule("issuer_name_present", "issuer_name", "ISSUER_NAME_MISSING", _QUO),
        RequiredFieldRule("currency_present", "currency", "CURRENCY_MISSING", _QUO),
        RequiredFieldRule("total_amount_present", "total_amount", "TOTAL_AMOUNT_MISSING", _QUO),
        CurrencyValidRule(),
        AmountPositiveRule("total_amount", "TOTAL_AMOUNT_NON_POSITIVE", _QUO),
        ValidityDateAfterIssueRule(),
        InvoiceTotalsConsistencyRule(),
        ExtractionReviewGateRule(),
    )


def _receipt_rules() -> tuple[BusinessValidationRule, ...]:
    return (
        RequiredFieldRule("merchant_name_present", "merchant_name", "MERCHANT_NAME_MISSING", _REC),
        RequiredFieldRule("transaction_date_present", "transaction_date", "TRANSACTION_DATE_MISSING", _REC),
        RequiredFieldRule("total_amount_present", "total_amount", "TOTAL_AMOUNT_MISSING", _REC),
        CurrencyValidRule(),
        AmountPositiveRule("total_amount", "TOTAL_AMOUNT_NON_POSITIVE", _REC),
        AmountNonNegativeRule("tax_amount", "TAX_AMOUNT_NEGATIVE", _REC),
        TaxNotExceedTotalRule(),
        ExtractionReviewGateRule(),
    )


def _generic_rules() -> tuple[BusinessValidationRule, ...]:
    return (ExtractionReviewGateRule(),)


class BusinessValidationRuleRegistry:
    def __init__(self) -> None:
        self._sets: dict[str, RuleSetDef] = {
            RULE_SET_INVOICE_V1: RuleSetDef(RULE_SET_INVOICE_V1, "1", _INV, _invoice_rules()),
            RULE_SET_QUOTE_V1: RuleSetDef(RULE_SET_QUOTE_V1, "1", _QUO, _quote_rules()),
            RULE_SET_RECEIPT_V1: RuleSetDef(RULE_SET_RECEIPT_V1, "1", _REC, _receipt_rules()),
            RULE_SET_GENERIC_V1: RuleSetDef(RULE_SET_GENERIC_V1, "1", _GEN, _generic_rules()),
        }

    def get(self, key: str) -> RuleSetDef:
        s = self._sets.get(key)
        if not s:
            raise BusinessValidationValidationError("rule_set_unknown", f"Rule set inconnu: {key}")
        return s

    def select_for_schema(self, schema_key: str) -> RuleSetDef:
        mapping = {
            "invoice_basic_v1": RULE_SET_INVOICE_V1,
            "quote_basic_v1": RULE_SET_QUOTE_V1,
            "receipt_basic_v1": RULE_SET_RECEIPT_V1,
            "generic_document_v1": RULE_SET_GENERIC_V1,
        }
        return self.get(mapping.get(schema_key, RULE_SET_GENERIC_V1))

    def execute(self, rule_set: RuleSetDef, ctx: RuleContext) -> list[ValidationIssueDraft]:
        issues: list[ValidationIssueDraft] = []
        for rule in rule_set.rules:
            if ctx.schema_key not in rule.supported_schemas and rule.supported_schemas:
                # ExtractionReviewGate supports all via its own set
                if ctx.schema_key not in getattr(rule, "supported_schemas", frozenset()):
                    continue
            issues.extend(rule.execute(ctx))
        return issues

    def list_public(self) -> list[dict]:
        return [
            {
                "key": s.key,
                "version": s.version,
                "schemas": sorted(s.schemas),
                "rules_count": len(s.rules),
            }
            for s in self._sets.values()
        ]


_REG: BusinessValidationRuleRegistry | None = None


def get_business_validation_rule_registry() -> BusinessValidationRuleRegistry:
    global _REG
    if _REG is None:
        _REG = BusinessValidationRuleRegistry()
    return _REG


def reset_business_validation_rule_registry_for_tests() -> None:
    global _REG
    _REG = None
