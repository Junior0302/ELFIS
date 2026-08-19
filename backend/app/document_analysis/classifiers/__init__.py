"""Classification initiale heuristique — sans IA."""

from __future__ import annotations

import io
import re
from typing import Any

from app.document_analysis.enums import DocumentClass

_PATTERNS: list[tuple[str, list[re.Pattern[str]], float]] = [
    (
        DocumentClass.INVOICE.value,
        [
            re.compile(r"\bfacture\b", re.I),
            re.compile(r"\binvoice\b", re.I),
            re.compile(r"\brechnung\b", re.I),
            re.compile(r"\btva\b", re.I),
            re.compile(r"\bvat\b", re.I),
        ],
        0.15,
    ),
    (
        DocumentClass.QUOTE.value,
        [
            re.compile(r"\bdevis\b", re.I),
            re.compile(r"\bquote\b", re.I),
            re.compile(r"\bquotation\b", re.I),
            re.compile(r"\bangebot\b", re.I),
        ],
        0.2,
    ),
    (
        DocumentClass.CREDIT_NOTE.value,
        [
            re.compile(r"\bavoir\b", re.I),
            re.compile(r"\bcredit\s*note\b", re.I),
            re.compile(r"\bgutschrift\b", re.I),
        ],
        0.25,
    ),
    (
        DocumentClass.BANK_STATEMENT.value,
        [
            re.compile(r"\brelevé\b", re.I),
            re.compile(r"\bbank\s*statement\b", re.I),
            re.compile(r"\biban\b", re.I),
            re.compile(r"\bsolde\b", re.I),
        ],
        0.18,
    ),
    (
        DocumentClass.CONTRACT.value,
        [
            re.compile(r"\bcontrat\b", re.I),
            re.compile(r"\bcontract\b", re.I),
            re.compile(r"\bvertrag\b", re.I),
            re.compile(r"\bconditions\s+générales\b", re.I),
        ],
        0.2,
    ),
    (
        DocumentClass.RECEIPT.value,
        [
            re.compile(r"\breçu\b", re.I),
            re.compile(r"\breceipt\b", re.I),
            re.compile(r"\bticket\b", re.I),
            re.compile(r"\bcaisse\b", re.I),
        ],
        0.2,
    ),
]


def _text_sample(content: bytes, technical: dict[str, Any], filename: str) -> str:
    parts = [filename or ""]
    fmt = technical.get("detected_format")
    if fmt == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    return " ".join(parts)
            for page in reader.pages[:3]:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    continue
        except Exception:
            pass
    elif fmt in {"csv", "json", "xml", "txt"}:
        parts.append(content[:4000].decode("utf-8", errors="ignore"))
    return "\n".join(parts)


def classify_document(
    content: bytes,
    *,
    filename: str,
    technical: dict[str, Any],
) -> dict[str, Any]:
    text = _text_sample(content, technical, filename)
    scores: dict[str, float] = {c.value: 0.0 for c in DocumentClass}
    hits: dict[str, list[str]] = {}
    for label, patterns, weight in _PATTERNS:
        matched = []
        for pat in patterns:
            if pat.search(text):
                scores[label] += weight
                matched.append(pat.pattern)
        if matched:
            hits[label] = matched

    # Filename hints
    fname = (filename or "").lower()
    if "facture" in fname or "invoice" in fname:
        scores[DocumentClass.INVOICE.value] += 0.25
    if "devis" in fname or "quote" in fname:
        scores[DocumentClass.QUOTE.value] += 0.25
    if "releve" in fname or "statement" in fname:
        scores[DocumentClass.BANK_STATEMENT.value] += 0.25

    best_label, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score < 0.2:
        return {
            "label": DocumentClass.UNKNOWN.value,
            "confidence": 0.2,
            "method": "heuristic",
            "scores": scores,
            "hits": hits,
        }
    confidence = min(0.95, 0.35 + best_score)
    return {
        "label": best_label,
        "confidence": round(confidence, 3),
        "method": "heuristic",
        "scores": scores,
        "hits": hits,
    }
