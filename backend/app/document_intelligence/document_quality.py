"""Qualité d'extraction déterministe + normalisation texte."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from app.config import settings

_STRUCTURING_WORDS = re.compile(
    r"(?i)\b(facture|invoice|total|tva|vat|date|num[eé]ro|number|montant|amount|ht|ttc)\b"
)
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NL = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normalisation Unicode déterministe — ne modifie pas les montants."""
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\x00", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in cleaned.split("\n"):
        line = _MULTI_SPACE.sub(" ", line).strip()
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = _MULTI_NL.sub("\n\n", cleaned).strip()
    return cleaned


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def calculate_quality(
    text: str,
    *,
    page_count: int | None = None,
) -> dict[str, Any]:
    """Évaluation déterministe (pas de LLM)."""
    pages = max(1, int(page_count or 1))
    length = len(text or "")
    min_chars = max(1, int(settings.elfis_document_min_text_characters))
    min_per_page = max(1, int(settings.elfis_document_min_text_per_page))

    if length == 0:
        return {
            "quality_score": 0.0,
            "confidence": 0.0,
            "requires_ocr": True,
            "requires_review": True,
            "warnings": ["no_text"],
        }

    printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
    alnum = sum(1 for c in text if c.isalnum())
    printable_ratio = printable / length
    alnum_ratio = alnum / length
    symbol_ratio = 1.0 - alnum_ratio
    chars_per_page = length / pages
    empty_pages_estimate = 1 if chars_per_page < min_per_page else 0
    has_structure = bool(_STRUCTURING_WORDS.search(text))

    score = 0.35
    score += min(0.35, length / 2000 * 0.35)
    score += 0.15 if printable_ratio > 0.9 else 0.0
    score += 0.1 if alnum_ratio > 0.4 else 0.0
    score += 0.1 if has_structure else 0.0
    score = max(0.0, min(1.0, score))

    warnings: list[str] = []
    requires_ocr = False
    requires_review = False

    if length < min_chars:
        requires_ocr = True
        warnings.append("text_too_short")
        score = min(score, 0.25)
    if chars_per_page < min_per_page:
        requires_ocr = True
        warnings.append("low_text_per_page")
        score = min(score, 0.35)
    if printable_ratio < 0.7:
        requires_review = True
        warnings.append("low_printable_ratio")
        score = min(score, 0.4)
    if symbol_ratio > 0.55:
        requires_review = True
        warnings.append("high_symbol_ratio")
    if empty_pages_estimate:
        warnings.append("possible_empty_pages")

    confidence = score
    if requires_ocr:
        confidence = min(confidence, 0.3)
        requires_review = True

    return {
        "quality_score": round(score, 4),
        "confidence": round(confidence, 4),
        "requires_ocr": requires_ocr,
        "requires_review": requires_review,
        "warnings": warnings,
        "metrics": {
            "text_length": length,
            "chars_per_page": round(chars_per_page, 2),
            "printable_ratio": round(printable_ratio, 4),
            "alnum_ratio": round(alnum_ratio, 4),
            "has_structuring_words": has_structure,
        },
    }
