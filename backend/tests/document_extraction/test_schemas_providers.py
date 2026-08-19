"""Tests schémas + providers + normalisation extraction."""

from __future__ import annotations

import asyncio

import pytest

from app.document_processing.extraction.exceptions import ExtractionValidationError
from app.document_processing.extraction.normalization import ExtractionNormalizationService
from app.document_processing.extraction.provider import ExtractionRequest
from app.document_processing.extraction.provider_registry import (
    get_extraction_provider_registry,
    reset_extraction_provider_registry_for_tests,
)
from app.document_processing.extraction.providers.noop import NoopExtractionProvider
from app.document_processing.extraction.providers.rules import RulesDocumentExtractionProvider
from app.document_processing.extraction.schema_registry import get_extraction_schema_registry
from app.document_processing.extraction.validation import ExtractionSchemaValidator


@pytest.fixture(autouse=True)
def _reset_regs():
    reset_extraction_provider_registry_for_tests()
    yield
    reset_extraction_provider_registry_for_tests()


def test_schema_registry_known():
    reg = get_extraction_schema_registry()
    inv = reg.get("invoice_basic_v1", "1")
    assert "invoice_number" in inv.required_fields
    assert "currency" in inv.required_fields
    assert inv.human_review_mandatory
    with pytest.raises(ExtractionValidationError):
        reg.get("unknown_schema_xyz", "1")


def test_provider_registry_noop_default(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "document_extraction_provider", "noop")
    reg = get_extraction_provider_registry()
    p = reg.configured()
    assert p.provider_key == "noop"
    with pytest.raises(ExtractionValidationError):
        reg.get("openai")


def test_noop_modes():
    p = NoopExtractionProvider()
    base = dict(
        document_id="d",
        document_version_id="v",
        organization_id=1,
        schema_key="invoice_basic_v1",
        schema_version="1",
        effective_document_type="invoice",
        source_text="",
    )
    ok = asyncio.run(p.extract(ExtractionRequest(**base, noop_mode="ok")))
    assert ok.success and "invoice_number" in ok.fields
    bad = asyncio.run(p.extract(ExtractionRequest(**base, noop_mode="retryable")))
    assert not bad.success and bad.retryable
    perm = asyncio.run(p.extract(ExtractionRequest(**base, noop_mode="permanent")))
    assert not perm.success and not perm.retryable


def test_rules_invoice_fr():
    text = """
    Facture N° F-2026-042
    Date d'émission : 15/01/2026
    Échéance : 15/02/2026
    Fournisseur : ACME SARL
    Client : Client Demo
    Total HT : 1 000,00
    TVA 20 % : 200,00
    Total TTC : 1 200,00 EUR
    """
    p = RulesDocumentExtractionProvider()
    res = asyncio.run(
        p.extract(
            ExtractionRequest(
                document_id="d",
                document_version_id="v",
                organization_id=1,
                schema_key="invoice_basic_v1",
                schema_version="1",
                effective_document_type="invoice",
                source_text=text,
            )
        )
    )
    assert res.success
    assert "invoice_number" in res.fields
    assert "total_amount" in res.fields
    assert "currency" in res.fields


def test_normalize_decimal_fr_en():
    n = ExtractionNormalizationService()
    assert str(n.normalize_decimal("1 234,56")) == "1234.56"
    assert str(n.normalize_decimal("1,234.56")) == "1234.56"
    assert n.normalize_currency("€") == "EUR"
    iso, amb = n.normalize_date("2026-01-15")
    assert iso == "2026-01-15" and not amb
    iso2, amb2 = n.normalize_date("03/04/2026")
    assert amb2 and iso2 is None


def test_schema_validator_missing_required():
    schema = get_extraction_schema_registry().get("invoice_basic_v1")
    v = ExtractionSchemaValidator()
    from app.document_processing.extraction.provider import ExtractedFieldPayload

    result = v.validate(
        schema,
        {
            "invoice_number": ExtractedFieldPayload(
                field_path="invoice_number", field_type="string", value="F-1"
            )
        },
    )
    assert not result.valid
    assert "currency" in result.missing_required_fields
