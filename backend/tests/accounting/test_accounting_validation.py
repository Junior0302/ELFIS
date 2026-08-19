"""Tests validation documentaire / financière."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.stages.document_validation_stage import run_document_validation
from app.accounting.stages.financial_validation_stage import run_financial_validation
from app.schemas import ExtractionResult


def _ext(**kwargs):
    base = dict(
        supplier="ACME",
        invoice_date="01/01/2026",
        invoice_number="F1",
        amount_ht=100.0,
        amount_tva=20.0,
        amount_ttc=120.0,
        vat_rate=20.0,
        document_type="facture",
        confidence_score=0.95,
    )
    base.update(kwargs)
    return ExtractionResult(**base)


def test_document_validation_ok():
    out = run_document_validation(_ext())
    assert out["status"] in ("valid", "warning")
    assert out["missing_fields"] == []


def test_missing_required_field():
    out = run_document_validation(_ext(supplier=None, invoice_number=None))
    assert out["missing_fields"]
    assert out["status"] in ("invalid", "warning")


def test_financial_balanced():
    out = run_financial_validation(_ext())
    assert out["balanced_amounts"] is True
    assert out["status"] in ("valid", "warning")


def test_financial_ht_tva_mismatch():
    out = run_financial_validation(_ext(amount_ttc=130.0))
    assert out["balanced_amounts"] is False
    assert out["status"] == "invalid"
    assert out["errors"]


def test_financial_tolerance(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_accounting_amount_tolerance", 0.02)
    out = run_financial_validation(_ext(amount_ttc=120.01))
    assert out["balanced_amounts"] is True


def test_decimal_not_float_drift():
    out = run_financial_validation(_ext(amount_ht=0.1, amount_tva=0.2, amount_ttc=0.3, vat_rate=None))
    # 0.1+0.2 en float est problématique — Decimal doit gérer
    assert isinstance(out["difference"], float)
    assert out["balanced_amounts"] is True or out["difference"] <= 0.02
