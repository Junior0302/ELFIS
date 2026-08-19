"""Tests sécurité Document Intelligence."""

from __future__ import annotations

import pytest

from app.document_intelligence.document_exceptions import DocumentValidationError
from app.document_intelligence.document_logging import safe_document_log_context
from app.document_intelligence.document_security import (
    assert_extension_matches_mime,
    assert_mime_allowed,
    assert_safe_storage_path,
    assert_text_size,
)


def test_mime_v1_allowed():
    assert assert_mime_allowed("application/pdf") == "application/pdf"
    assert assert_mime_allowed("text/plain") == "text/plain"


def test_prepared_images_not_active_by_default():
    with pytest.raises(DocumentValidationError):
        assert_mime_allowed("image/png")


def test_extension_mismatch():
    with pytest.raises(DocumentValidationError):
        assert_extension_matches_mime("doc.txt", "application/pdf")


def test_path_traversal_rejected():
    with pytest.raises(DocumentValidationError):
        assert_safe_storage_path("../etc/passwd")
    with pytest.raises(DocumentValidationError):
        assert_safe_storage_path("/absolute/path")


def test_text_too_large_not_truncated(monkeypatch):
    monkeypatch.setattr("app.config.settings.elfis_document_max_extracted_text_bytes", 2048)
    with pytest.raises(DocumentValidationError) as exc:
        assert_text_size("x" * 3000)
    assert "trop volumineux" in exc.value.message


def test_safe_log_excludes_text():
    ctx = safe_document_log_context(
        extraction_id="e1",
        text_content="SECRET TEXT",  # type: ignore[call-arg]
        text="SECRET",
        pdf=b"%PDF",
        api_key="sk-x",
    )
    assert "text_content" not in ctx
    assert "text" not in ctx
    assert "pdf" not in ctx
    assert "api_key" not in ctx
    assert ctx["extraction_id"] == "e1"
