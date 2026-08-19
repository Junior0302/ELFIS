"""Tests providers OCR + sélection."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.document_processing.ocr.exceptions import OCRValidationError
from app.document_processing.ocr.provider import OCRRequest
from app.document_processing.ocr.provider_registry import get_ocr_provider_registry
from app.document_processing.ocr.providers.native_pdf_text import NativePdfTextProvider
from app.document_processing.ocr.providers.noop import NoopOCRProvider
from app.document_processing.ocr.selection import OCRProviderSelectionService


def test_registry_noop_default(monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "noop")
    reg = get_ocr_provider_registry()
    assert reg.configured_key() == "noop"
    assert reg.get("noop").provider_key == "noop"


def test_registry_unknown(monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "cloud_xyz")
    with pytest.raises(OCRValidationError):
        get_ocr_provider_registry().configured_key()


def test_noop_modes():
    p = NoopOCRProvider()

    async def run(mode):
        return await p.recognize(
            OCRRequest(
                document_id="d",
                document_version_id="v",
                mime_type="application/pdf",
                noop_mode=mode,
            )
        )

    ok = asyncio.run(run("ok"))
    assert ok.success and len(ok.pages) >= 1
    assert "noop" in ok.extraction_method
    bad = asyncio.run(run("retryable"))
    assert not bad.success and bad.retryable
    perm = asyncio.run(run("permanent"))
    assert not perm.success and not perm.retryable


def test_native_pdf_text(tmp_path):
    # PDF minimal via reportlab or pypdf writer
    from pypdf import PdfWriter
    from io import BytesIO

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # blank has no text — OK
    path = tmp_path / "blank.pdf"
    with path.open("wb") as f:
        writer.write(f)

    provider = NativePdfTextProvider()
    res = asyncio.run(
        provider.recognize(
            OCRRequest(
                document_id="d",
                document_version_id="v",
                mime_type="application/pdf",
                temp_path=path,
                max_pages=5,
            )
        )
    )
    assert res.success
    assert res.extraction_method == "native_pdf_text"
    assert len(res.pages) == 1


def test_selection_noop(monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "noop")
    sel = OCRProviderSelectionService().select(mime_type="application/pdf")
    assert sel.selected_provider == "noop"
    assert sel.reason_code == "configured_noop"


def test_selection_native(monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "native_pdf")
    monkeypatch.setattr("app.config.settings.document_ocr_native_pdf_text_enabled", True)
    sel = OCRProviderSelectionService().select(mime_type="application/pdf")
    assert sel.selected_provider == "native_pdf"


def test_selection_image_unavailable(monkeypatch):
    monkeypatch.setattr("app.config.settings.document_ocr_provider", "native_pdf")
    with pytest.raises(OCRValidationError):
        OCRProviderSelectionService().select(mime_type="image/png")
