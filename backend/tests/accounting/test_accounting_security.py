"""Tests sécurité Accounting."""

from __future__ import annotations

import pytest

from app.accounting.accounting_exceptions import AccountingPermissionError, AccountingValidationError
from app.accounting.accounting_logging import safe_accounting_log_context
from app.accounting.accounting_security import (
    assert_account_code,
    assert_description,
    check_accounting_permission,
    to_decimal,
)


def test_account_code_validation():
    assert assert_account_code("607000") == "607000"
    with pytest.raises(AccountingValidationError):
        assert_account_code("abc")
    with pytest.raises(AccountingValidationError):
        assert_account_code("12")


def test_description_rejects_script():
    with pytest.raises(AccountingValidationError):
        assert_description("<script>alert(1)</script>")


def test_decimal_conversion():
    d = to_decimal("10.126")
    assert str(d) == "10.13"


def test_permissions_star_and_fallback():
    check_accounting_permission(["*"], "validate")
    check_accounting_permission(["ai.analysis"], "view")
    with pytest.raises(AccountingPermissionError):
        check_accounting_permission(["invoice.read"], "validate")


def test_safe_log_excludes_sensitive():
    ctx = safe_accounting_log_context(
        proposal_id="p1",
        lines=[{"a": 1}],
        pdf=b"%PDF",
        api_key="sk",
        extracted_text="SECRET",
    )
    assert "lines" not in ctx
    assert "pdf" not in ctx
    assert "api_key" not in ctx
    assert ctx["proposal_id"] == "p1"
