"""Tests validation métier documentaire RC2.5.5."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.document_processing.validation.rule_base import RuleContext
from app.document_processing.validation.rule_registry import get_business_validation_rule_registry
from app.document_processing.validation.types import (
    PIPELINE_BUSINESS_VALIDATION_V1,
    RULE_SET_INVOICE_V1,
)
from app.document_processing.step_registry import get_pipeline_registry, reset_pipeline_registry_for_tests


def _fields(**kwargs):
    return {k: {"normalized_value": v, "value": v} for k, v in kwargs.items()}


def test_pipeline_business_validation_registered():
    reset_pipeline_registry_for_tests()
    reg = get_pipeline_registry()
    assert PIPELINE_BUSINESS_VALIDATION_V1 in reg.known_pipelines()
    pipe = reg.get_pipeline(PIPELINE_BUSINESS_VALIDATION_V1)
    assert len(pipe.steps) == 9


def test_invoice_valid_totals():
    reg = get_business_validation_rule_registry()
    rs = reg.get(RULE_SET_INVOICE_V1)
    ctx = RuleContext(
        schema_key="invoice_basic_v1",
        document_type="supplier_invoice",
        fields=_fields(
            invoice_number="F-1",
            issue_date="2026-01-15",
            supplier_name="ACME",
            currency="EUR",
            subtotal="100.00",
            tax_amount="20.00",
            total_amount="120.00",
            tax_rate="20",
        ),
        amount_tolerance=Decimal("0.02"),
        percentage_tolerance=Decimal("0.01"),
        extraction_status="confirmed",
        extraction_requires_review=False,
    )
    issues = reg.execute(rs, ctx)
    blocking = [i for i in issues if i.blocking]
    assert blocking == []


def test_invoice_total_mismatch():
    reg = get_business_validation_rule_registry()
    rs = reg.get(RULE_SET_INVOICE_V1)
    ctx = RuleContext(
        schema_key="invoice_basic_v1",
        document_type="supplier_invoice",
        fields=_fields(
            invoice_number="F-1",
            issue_date="2026-01-15",
            supplier_name="ACME",
            currency="EUR",
            subtotal="100.00",
            tax_amount="20.00",
            total_amount="150.00",
        ),
        amount_tolerance=Decimal("0.02"),
        percentage_tolerance=Decimal("0.01"),
        extraction_status="confirmed",
        extraction_requires_review=False,
    )
    issues = reg.execute(rs, ctx)
    codes = {i.issue_code for i in issues}
    assert any("TOTAL" in c or "MISMATCH" in c or "ROUNDING" in c for c in codes) or any(
        i.blocking for i in issues
    )


def test_invoice_rounding_tolerance():
    reg = get_business_validation_rule_registry()
    rs = reg.get(RULE_SET_INVOICE_V1)
    ctx = RuleContext(
        schema_key="invoice_basic_v1",
        document_type="supplier_invoice",
        fields=_fields(
            invoice_number="F-1",
            issue_date="2026-01-15",
            supplier_name="ACME",
            currency="EUR",
            subtotal="100.00",
            tax_amount="20.00",
            total_amount="120.01",
        ),
        amount_tolerance=Decimal("0.02"),
        percentage_tolerance=Decimal("0.01"),
        extraction_status="confirmed",
        extraction_requires_review=False,
    )
    issues = reg.execute(rs, ctx)
    blocking = [i for i in issues if i.blocking]
    assert blocking == []


def test_negative_amount_blocked():
    reg = get_business_validation_rule_registry()
    rs = reg.get(RULE_SET_INVOICE_V1)
    ctx = RuleContext(
        schema_key="invoice_basic_v1",
        document_type="supplier_invoice",
        fields=_fields(
            invoice_number="F-1",
            issue_date="2026-01-15",
            supplier_name="ACME",
            currency="EUR",
            subtotal="-1",
            tax_amount="0",
            total_amount="-1",
        ),
        amount_tolerance=Decimal("0.02"),
        percentage_tolerance=Decimal("0.01"),
        extraction_status="confirmed",
        extraction_requires_review=False,
    )
    issues = reg.execute(rs, ctx)
    assert any(i.blocking for i in issues)


def test_invalid_currency():
    reg = get_business_validation_rule_registry()
    rs = reg.get(RULE_SET_INVOICE_V1)
    ctx = RuleContext(
        schema_key="invoice_basic_v1",
        document_type="supplier_invoice",
        fields=_fields(
            invoice_number="F-1",
            issue_date="2026-01-15",
            supplier_name="ACME",
            currency="EURO",
            total_amount="10",
        ),
        amount_tolerance=Decimal("0.02"),
        percentage_tolerance=Decimal("0.01"),
        extraction_status="confirmed",
        extraction_requires_review=False,
    )
    issues = reg.execute(rs, ctx)
    assert any(i.issue_code == "CURRENCY_INVALID" for i in issues)


def test_due_date_before_issue():
    reg = get_business_validation_rule_registry()
    rs = reg.get(RULE_SET_INVOICE_V1)
    ctx = RuleContext(
        schema_key="invoice_basic_v1",
        document_type="supplier_invoice",
        fields=_fields(
            invoice_number="F-1",
            issue_date="2026-02-01",
            due_date="2026-01-01",
            supplier_name="ACME",
            currency="EUR",
            total_amount="10",
        ),
        amount_tolerance=Decimal("0.02"),
        percentage_tolerance=Decimal("0.01"),
        extraction_status="confirmed",
        extraction_requires_review=False,
    )
    issues = reg.execute(rs, ctx)
    assert any(i.blocking or i.severity in ("error", "warning") for i in issues)


def test_quote_and_receipt_rule_sets():
    reg = get_business_validation_rule_registry()
    assert reg.select_for_schema("quote_basic_v1").key.startswith("quote_")
    assert reg.select_for_schema("receipt_basic_v1").key.startswith("receipt_")
    assert reg.select_for_schema("generic_document_v1").key.startswith("generic_")


def test_issue_params_no_raw_amounts_in_sanitizer():
    from app.document_processing.validation.sanitization import sanitize_issue_parameters

    out = sanitize_issue_parameters({"difference_category": "above_tolerance", "amount": "999.99"})
    assert "difference_category" in out
    assert "amount" not in out
