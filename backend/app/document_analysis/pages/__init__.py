"""Comptage de pages — lecture seule."""

from __future__ import annotations

from typing import Any


def analyze_pages(technical: dict[str, Any]) -> dict[str, Any]:
    pdf = technical.get("pdf") or {}
    fmt = technical.get("detected_format")
    page_count = pdf.get("page_count")
    if page_count is None and technical.get("is_image"):
        page_count = 1
    if page_count is None and fmt in {"csv", "json", "xml", "txt"}:
        page_count = 1
    if page_count is None and technical.get("zip", {}).get("is_zip"):
        page_count = None  # archive — pas de pages document
    return {
        "page_count": page_count,
        "empty_page_estimate": 0,
        "multi_page": bool(page_count and page_count > 1),
    }
