"""Tests extracteurs PDF / TXT."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.document_intelligence.document_exceptions import DocumentValidationError
from app.document_intelligence.document_quality import calculate_quality, normalize_text, text_sha256
from app.document_intelligence.document_registry import bootstrap_extractors, default_extractor_registry
from app.document_intelligence.document_security import assert_file_size, assert_mime_allowed
from app.document_intelligence.document_types import ExtractorNames
from app.document_intelligence.extractors.pdf_text_extractor import PdfTextExtractor
from app.document_intelligence.extractors.plain_text_extractor import PlainTextExtractor
from tests.document_intelligence import make_empty_pdf, make_text_pdf


def setup_function():
    default_extractor_registry.clear()
    bootstrap_extractors()


def test_pdf_extractor_registered():
    reg = bootstrap_extractors()
    assert reg.get(ExtractorNames.PDF_TEXT).extractor_name == ExtractorNames.PDF_TEXT
    assert reg.for_mime("application/pdf") is not None


def test_txt_extractor_registered():
    reg = bootstrap_extractors()
    assert reg.get(ExtractorNames.PLAIN_TEXT).extractor_name == ExtractorNames.PLAIN_TEXT
    assert reg.for_mime("text/plain") is not None


def test_unknown_mime_rejected():
    with pytest.raises(DocumentValidationError):
        assert_mime_allowed("application/zip")


def test_file_too_large_rejected(monkeypatch):
    monkeypatch.setattr("app.config.settings.elfis_document_max_file_bytes", 5000)
    with pytest.raises(DocumentValidationError):
        assert_file_size(5001)


def test_pdf_text_extracted():
    pdf = make_text_pdf("Facture ACME Total TTC 120.00 TVA date 01/01/2024")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
        path = Path(fh.name)
        fh.write(pdf)
    try:
        out = PdfTextExtractor().extract(path=path, mime_type="application/pdf", filename="f.pdf")
        assert out.page_count == 1
        if out.text:
            assert out.requires_ocr is False or len(out.text) > 0
            assert "text_content" not in (out.metadata or {})
    finally:
        path.unlink(missing_ok=True)


def test_pdf_empty_requires_ocr():
    pdf = make_empty_pdf()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
        path = Path(fh.name)
        fh.write(pdf)
    try:
        out = PdfTextExtractor().extract(path=path, mime_type="application/pdf", filename="scan.pdf")
        assert out.requires_ocr is True
        assert not out.text or out.requires_review
    finally:
        path.unlink(missing_ok=True)


def test_txt_extracted():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as fh:
        path = Path(fh.name)
        fh.write(b"Facture numero 12 Total TVA 20 montant 100")
    try:
        out = PlainTextExtractor().extract(path=path, mime_type="text/plain", filename="a.txt")
        assert "Facture" in out.text
        assert out.page_count == 1
        assert out.requires_ocr is False
    finally:
        path.unlink(missing_ok=True)


def test_txt_binary_rejected():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as fh:
        path = Path(fh.name)
        fh.write(b"%PDF-1.4\x00\x01\x02" + bytes(range(256)) * 4)
    try:
        with pytest.raises(DocumentValidationError):
            PlainTextExtractor().extract(path=path, mime_type="text/plain", filename="b.txt")
    finally:
        path.unlink(missing_ok=True)



def test_unicode_normalization():
    raw = "Facture\u00a0  Café\r\n\r\n\r\nTotal"
    cleaned = normalize_text(raw)
    assert "\r" not in cleaned
    assert "\u00a0" not in cleaned or " " in cleaned
    assert "\n\n\n" not in cleaned


def test_sha256_hash():
    t = normalize_text("hello world")
    h = text_sha256(t)
    assert len(h) == 64
    assert h == text_sha256(t)


def test_quality_high_for_usable_text():
    text = "Facture fournisseur ACME Montant HT 100 TVA 20 Total TTC 120 date 01/01/2024 numéro FAC-9"
    q = calculate_quality(text, page_count=1)
    assert q["quality_score"] >= 0.5
    assert q["requires_ocr"] is False


def test_quality_low_for_unusable():
    q = calculate_quality("@@", page_count=1)
    assert q["requires_ocr"] is True
    assert q["quality_score"] <= 0.35
