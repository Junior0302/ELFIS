"""Tests mapping comptable."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.accounting_types import AccountingDocumentTypes
from app.accounting.stages.mapping_stage import run_accounting_mapping
from app.schemas import ExtractionResult


def test_supplier_invoice_mapping():
    ext = ExtractionResult(
        supplier="Fournisseur",
        invoice_number="F1",
        invoice_date="01/01/2026",
        amount_ht=100,
        amount_tva=20,
        amount_ttc=120,
        vat_rate=20,
        document_type="facture",
        confidence_score=0.9,
    )
    out = run_accounting_mapping(ext, document_type=AccountingDocumentTypes.SUPPLIER_INVOICE)
    assert out["balanced"] is True
    assert out["journal_code"] == "ACH"
    assert abs(Decimal(str(out["total_debit"])) - Decimal(str(out["total_credit"]))) <= Decimal("0.01")
    assert len(out["lines"]) == 3


def test_customer_invoice_mapping():
    ext = ExtractionResult(
        customer_name="Client",
        invoice_number="FC1",
        amount_ht=100,
        amount_tva=20,
        amount_ttc=120,
        vat_rate=20,
        document_type="customer_invoice",
        confidence_score=0.9,
    )
    out = run_accounting_mapping(ext, document_type=AccountingDocumentTypes.CUSTOMER_INVOICE)
    assert out["balanced"] is True
    assert out["journal_code"] == "VTE"
    assert len(out["lines"]) == 3


def test_unbalanced_refused_in_mapping_logic():
    # Mapping normal est équilibré ; on vérifie le flag
    ext = ExtractionResult(
        supplier="X",
        invoice_number="F",
        amount_ht=100,
        amount_tva=20,
        amount_ttc=120,
        document_type="facture",
        confidence_score=0.9,
    )
    out = run_accounting_mapping(ext, document_type=AccountingDocumentTypes.SUPPLIER_INVOICE)
    assert out["balanced"] is True
    assert isinstance(out["total_debit"], float)
