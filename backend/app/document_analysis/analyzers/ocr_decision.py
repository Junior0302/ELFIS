"""Décision OCR — ne lance jamais l'OCR."""

from __future__ import annotations

from typing import Any


def decide_ocr(technical: dict[str, Any], language: dict[str, Any]) -> dict[str, Any]:
    fmt = technical.get("detected_format")
    pdf = technical.get("pdf") or {}

    if fmt in {"csv", "json", "xml", "txt"}:
        return {
            "need_ocr": False,
            "reason": "structured_text_format",
            "confidence": 0.99,
        }
    if fmt == "zip":
        return {
            "need_ocr": False,
            "reason": "archive_inventory_only",
            "confidence": 0.9,
        }
    if technical.get("is_image"):
        return {
            "need_ocr": True,
            "reason": "raster_image",
            "confidence": 0.95,
        }
    if fmt == "pdf":
        if pdf.get("is_encrypted") and not pdf.get("has_text"):
            return {
                "need_ocr": True,
                "reason": "encrypted_or_unreadable_pdf",
                "confidence": 0.7,
            }
        if pdf.get("has_text") and not pdf.get("probable_scan"):
            return {
                "need_ocr": False,
                "reason": "pdf_with_extractable_text",
                "confidence": 0.92,
            }
        if pdf.get("probable_scan") or not pdf.get("has_text"):
            return {
                "need_ocr": True,
                "reason": "scanned_or_image_pdf",
                "confidence": 0.9,
            }
    # Fallback
    if language.get("code") == "unknown" and language.get("sample_chars", 0) < 20:
        return {
            "need_ocr": True,
            "reason": "no_extractable_text",
            "confidence": 0.75,
        }
    return {
        "need_ocr": False,
        "reason": "default_text_assumed",
        "confidence": 0.4,
    }
