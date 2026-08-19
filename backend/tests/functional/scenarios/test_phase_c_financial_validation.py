"""Phase C — Validation financière (FIN-001 … FIN-004)."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.accounting_security import amount_tolerance
from app.accounting.stages.financial_validation_stage import run_financial_validation
from app.agents.validator import validate_financials
from app.schemas import ExtractionResult


def _ext(**kwargs) -> ExtractionResult:
    base = dict(
        supplier="Fictif SA",
        invoice_number="FAC-1",
        invoice_date="2026-07-01",
        amount_ht=100.0,
        amount_tva=20.0,
        amount_ttc=120.0,
        vat_rate=20.0,
        currency="EUR",
        document_type="supplier_invoice",
        confidence_score=0.95,
    )
    base.update(kwargs)
    return ExtractionResult(**base)


def test_fin_001_valid_totals():
    outcome = run_financial_validation(_ext())
    assert outcome["status"] in ("valid", "warning")
    assert outcome["balanced_amounts"] is True
    legacy = validate_financials(_ext())
    assert legacy is not None


def test_fin_002_unbalanced_detected():
    outcome = run_financial_validation(_ext(amount_ttc=999.0))
    assert outcome["balanced_amounts"] is False
    assert outcome["status"] == "invalid"
    assert outcome["errors"]


def test_fin_003_rounding_tolerance_documented():
    tol = amount_tolerance()
    assert Decimal(str(tol)) <= Decimal("0.05")
    assert Decimal(str(tol)) >= Decimal("0.01")
    # Écart 0.01 dans tolérance 0.02
    outcome = run_financial_validation(_ext(amount_ttc=120.01))
    assert outcome["balanced_amounts"] is True
    assert outcome["status"] in ("valid", "warning")


def test_fin_004_credit_note_negative_coherent():
    outcome = run_financial_validation(
        _ext(
            document_type="credit_note",
            amount_ht=-50.0,
            amount_tva=-10.0,
            amount_ttc=-60.0,
        )
    )
    assert outcome["balanced_amounts"] is True
    assert not any("négatif" in e.lower() for e in outcome.get("errors") or [])
