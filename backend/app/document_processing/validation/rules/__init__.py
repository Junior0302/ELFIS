"""Règles facture / devis / reçu / générique — Decimal uniquement."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.document_processing.validation.rule_base import RuleContext, ValidationIssueDraft


def _get(fields: dict[str, Any], path: str) -> Any:
    f = fields.get(path)
    if isinstance(f, dict):
        return f.get("normalized_value", f.get("value"))
    return f


def _dec(val: Any) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def _req(path: str, ctx: RuleContext, *, rule_key: str, code: str) -> list[ValidationIssueDraft]:
    if _get(ctx.fields, path) in (None, ""):
        return [
            ValidationIssueDraft(
                rule_key=rule_key,
                rule_version="1",
                severity="error",
                issue_code=code,
                field_paths=[path],
                parameters={"expected_presence": "required"},
                blocking=True,
                message_code=code,
            )
        ]
    return []


class RequiredFieldRule:
    def __init__(self, rule_key: str, path: str, issue_code: str, schemas: frozenset[str]):
        self.rule_key = rule_key
        self.rule_version = "1"
        self.path = path
        self.issue_code = issue_code
        self.supported_schemas = schemas
        self.severity = "error"
        self.blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        if ctx.schema_key not in self.supported_schemas:
            return []
        return _req(self.path, ctx, rule_key=self.rule_key, code=self.issue_code)


class CurrencyValidRule:
    rule_key = "currency_valid"
    rule_version = "1"
    supported_schemas = frozenset({"invoice_basic_v1", "quote_basic_v1", "receipt_basic_v1"})
    severity = "error"
    blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        if ctx.schema_key not in self.supported_schemas:
            return []
        cur = _get(ctx.fields, "currency")
        if cur is None or cur == "":
            return []  # required field handled elsewhere
        s = str(cur).strip().upper()
        if len(s) != 3 or not s.isalpha():
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity=self.severity,
                    issue_code="CURRENCY_INVALID",
                    field_paths=["currency"],
                    parameters={"reason": "not_iso4217"},
                    blocking=True,
                    message_code="CURRENCY_INVALID",
                )
            ]
        return []


class AmountPositiveRule:
    def __init__(self, path: str, issue_code: str, schemas: frozenset[str], *, allow_zero: bool = False):
        self.rule_key = f"{path}_positive"
        self.rule_version = "1"
        self.path = path
        self.issue_code = issue_code
        self.supported_schemas = schemas
        self.allow_zero = allow_zero
        self.severity = "error"
        self.blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        if ctx.schema_key not in self.supported_schemas:
            return []
        val = _dec(_get(ctx.fields, self.path))
        if val is None:
            return []
        if val < 0 or (not self.allow_zero and val == 0 and self.path == "total_amount"):
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity=self.severity,
                    issue_code=self.issue_code,
                    field_paths=[self.path],
                    parameters={"reason": "non_positive"},
                    blocking=True,
                    message_code=self.issue_code,
                )
            ]
        return []


class AmountNonNegativeRule:
    def __init__(self, path: str, issue_code: str, schemas: frozenset[str]):
        self.rule_key = f"{path}_non_negative"
        self.rule_version = "1"
        self.path = path
        self.issue_code = issue_code
        self.supported_schemas = schemas
        self.severity = "error"
        self.blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        if ctx.schema_key not in self.supported_schemas:
            return []
        val = _dec(_get(ctx.fields, self.path))
        if val is None:
            return []
        if val < 0:
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity=self.severity,
                    issue_code=self.issue_code,
                    field_paths=[self.path],
                    parameters={"reason": "negative"},
                    blocking=True,
                    message_code=self.issue_code,
                )
            ]
        return []


class InvoiceTotalsConsistencyRule:
    rule_key = "invoice_totals_consistency"
    rule_version = "1"
    supported_schemas = frozenset({"invoice_basic_v1", "quote_basic_v1"})
    severity = "error"
    blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        if ctx.schema_key not in self.supported_schemas:
            return []
        sub = _dec(_get(ctx.fields, "subtotal"))
        tax = _dec(_get(ctx.fields, "tax_amount"))
        tot = _dec(_get(ctx.fields, "total_amount"))
        if sub is None or tax is None or tot is None:
            return []
        diff = abs((sub + tax) - tot)
        if diff <= ctx.amount_tolerance:
            if diff > 0:
                return [
                    ValidationIssueDraft(
                        rule_key=self.rule_key,
                        rule_version=self.rule_version,
                        severity="warning",
                        issue_code="INVOICE_TOTAL_ROUNDING_DIFFERENCE",
                        field_paths=["subtotal", "tax_amount", "total_amount"],
                        parameters={
                            "difference_category": "within_tolerance",
                            "tolerance_applied": True,
                        },
                        blocking=False,
                        message_code="INVOICE_TOTAL_ROUNDING_DIFFERENCE",
                    )
                ]
            return []
        return [
            ValidationIssueDraft(
                rule_key=self.rule_key,
                rule_version=self.rule_version,
                severity="error",
                issue_code="INVOICE_TOTAL_MISMATCH",
                field_paths=["subtotal", "tax_amount", "total_amount"],
                parameters={"difference_category": "above_tolerance", "tolerance_applied": True},
                blocking=True,
                message_code="INVOICE_TOTAL_MISMATCH",
            )
        ]


class DueDateAfterIssueRule:
    rule_key = "due_date_after_issue"
    rule_version = "1"
    supported_schemas = frozenset({"invoice_basic_v1"})
    severity = "error"
    blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        issue = _get(ctx.fields, "issue_date")
        due = _get(ctx.fields, "due_date")
        if not issue or not due:
            return []
        # seulement dates ISO certaines
        if not (isinstance(issue, str) and isinstance(due, str)):
            return []
        if len(issue) < 10 or len(due) < 10:
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity="warning",
                    issue_code="DATE_AMBIGUOUS_REVIEW",
                    field_paths=["issue_date", "due_date"],
                    parameters={"reason": "uncertain"},
                    blocking=False,
                    message_code="DATE_AMBIGUOUS_REVIEW",
                )
            ]
        if due < issue:
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity=self.severity,
                    issue_code="DUE_DATE_BEFORE_ISSUE",
                    field_paths=["issue_date", "due_date"],
                    parameters={"comparison": "due_lt_issue"},
                    blocking=True,
                    message_code="DUE_DATE_BEFORE_ISSUE",
                )
            ]
        return []


class TaxRateRangeRule:
    rule_key = "tax_rate_range"
    rule_version = "1"
    supported_schemas = frozenset({"invoice_basic_v1"})
    severity = "warning"
    blocking = False

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        rate = _dec(_get(ctx.fields, "tax_rate"))
        if rate is None:
            return []
        if rate < 0 or rate > 100:
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity="error",
                    issue_code="TAX_RATE_OUT_OF_RANGE",
                    field_paths=["tax_rate"],
                    parameters={"range": "0_100"},
                    blocking=True,
                    message_code="TAX_RATE_OUT_OF_RANGE",
                )
            ]
        return []


class TaxNotExceedTotalRule:
    rule_key = "tax_not_exceed_total"
    rule_version = "1"
    supported_schemas = frozenset({"receipt_basic_v1", "invoice_basic_v1"})
    severity = "error"
    blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        tax = _dec(_get(ctx.fields, "tax_amount"))
        tot = _dec(_get(ctx.fields, "total_amount"))
        if tax is None or tot is None:
            return []
        if tax > tot + ctx.amount_tolerance:
            return [
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity=self.severity,
                    issue_code="TAX_EXCEEDS_TOTAL",
                    field_paths=["tax_amount", "total_amount"],
                    parameters={"comparison": "tax_gt_total"},
                    blocking=True,
                    message_code="TAX_EXCEEDS_TOTAL",
                )
            ]
        return []


class ExtractionReviewGateRule:
    rule_key = "extraction_review_gate"
    rule_version = "1"
    supported_schemas = frozenset(
        {"invoice_basic_v1", "quote_basic_v1", "receipt_basic_v1", "generic_document_v1"}
    )
    severity = "warning"
    blocking = False

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        out: list[ValidationIssueDraft] = []
        if ctx.extraction_status == "invalid":
            out.append(
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity="critical",
                    issue_code="EXTRACTION_INVALID_BLOCK",
                    field_paths=[],
                    parameters={"reason": "extraction_invalid"},
                    blocking=True,
                    message_code="EXTRACTION_INVALID_BLOCK",
                )
            )
        if ctx.extraction_requires_review:
            out.append(
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity="warning",
                    issue_code="EXTRACTION_REQUIRES_REVIEW",
                    field_paths=[],
                    parameters={"reason": "requires_review"},
                    blocking=False,
                    message_code="EXTRACTION_REQUIRES_REVIEW",
                )
            )
        if ctx.classification_ambiguous:
            out.append(
                ValidationIssueDraft(
                    rule_key=self.rule_key,
                    rule_version=self.rule_version,
                    severity="warning",
                    issue_code="CLASSIFICATION_AMBIGUOUS_REVIEW",
                    field_paths=[],
                    parameters={"reason": "ambiguous_invoice"},
                    blocking=False,
                    message_code="CLASSIFICATION_AMBIGUOUS_REVIEW",
                )
            )
        return out


class ValidityDateAfterIssueRule:
    rule_key = "validity_after_issue"
    rule_version = "1"
    supported_schemas = frozenset({"quote_basic_v1"})
    severity = "error"
    blocking = True

    def execute(self, ctx: RuleContext) -> list[ValidationIssueDraft]:
        issue = _get(ctx.fields, "issue_date")
        valid = _get(ctx.fields, "validity_date")
        if not issue or not valid:
            return []
        if isinstance(issue, str) and isinstance(valid, str) and len(issue) >= 10 and len(valid) >= 10:
            if valid < issue:
                return [
                    ValidationIssueDraft(
                        rule_key=self.rule_key,
                        rule_version=self.rule_version,
                        severity=self.severity,
                        issue_code="VALIDITY_BEFORE_ISSUE",
                        field_paths=["issue_date", "validity_date"],
                        parameters={"comparison": "validity_lt_issue"},
                        blocking=True,
                        message_code="VALIDITY_BEFORE_ISSUE",
                    )
                ]
        return []
