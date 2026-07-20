"""Tests tâches documentaires + sécurité input."""

from __future__ import annotations

import pytest

from app.ai.ai_context import AIContext
from app.ai.ai_exceptions import AIValidationError
from app.ai.ai_security import assert_safe_ai_input
from app.ai.ai_schemas import AIProviderResponse
from app.ai.tasks.document_classification import DocumentClassifyTask
from app.ai.tasks.document_extraction import DocumentExtractInvoiceTask
from app.ai.tasks.document_quality import DocumentQualityCheckTask


class _Mock:
    def execute_structured(self, **kwargs):
        return AIProviderResponse(
            content="{}",
            structured_output={
                "document_type": "supplier_invoice",
                "confidence": 0.91,
                "possible_types": [{"type": "supplier_invoice", "confidence": 0.91}],
                "reason": "llm",
            },
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
        )


def test_classification_success():
    task = DocumentClassifyTask()
    out = task.execute(
        {"extracted_text": "Facture fournisseur ACME HT 100 TVA 20 TTC 120", "filename": "f.pdf"},
        AIContext(model="gpt-4o-mini"),
        _Mock(),
    )
    validated = task.validate_output(out)
    assert validated["document_type"] == "supplier_invoice"
    assert validated["confidence"] >= 0.9


def test_classification_low_confidence_review():
    task = DocumentClassifyTask()
    out = task.execute(
        {"extracted_text": "x", "filename": "f.pdf"},
        AIContext(model="gpt-4o-mini"),
        None,
    )
    validated = task.validate_output(out)
    assert validated["requires_review"] is True


def test_extraction_compatible_schema():
    task = DocumentExtractInvoiceTask()
    out = task.execute(
        {
            "extracted_text": "Facture FAC-99 Société Test Montant HT 50,00 TVA 10,00 TTC 60,00",
            "filename": "inv.pdf",
            "document_type": "supplier_invoice",
        },
        AIContext(model="gpt-4o-mini"),
        None,  # heuristique reader
    )
    validated = task.validate_output(out)
    assert "supplier" in validated
    assert "amounts" in validated
    assert "compatible_extraction" in validated
    assert "pdf" not in validated


def test_quality_deterministic_financial_error():
    task = DocumentQualityCheckTask()
    out = task.execute(
        {
            "extraction": {
                "supplier": "A",
                "invoice_date": "01-01-2024",
                "invoice_number": "1",
                "amount_ht": 100.0,
                "amount_tva": 20.0,
                "amount_ttc": 999.0,
                "vat_rate": 20.0,
                "document_type": "facture",
                "confidence_score": 0.9,
            }
        },
        AIContext(),
        None,
    )
    validated = task.validate_output(out)
    assert validated["status"] in ("warning", "invalid")
    assert validated["financial_checks"]["ht_plus_tva_equals_ttc"] is False
    assert any("TTC" in e for e in validated["errors"])


def test_no_pdf_in_safe_input():
    with pytest.raises(AIValidationError):
        assert_safe_ai_input({"extracted_text": "%PDF-1.4 binary"}, max_bytes=10000)
