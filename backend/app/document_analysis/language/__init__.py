"""Détection de langue — heuristiques (pas de LLM)."""

from __future__ import annotations

import io
import re
from typing import Any

from app.document_analysis.enums import LanguageCode

# Mots fonctionnels fréquents par langue
_STOPWORDS: dict[str, set[str]] = {
    LanguageCode.FR.value: {
        "le", "la", "les", "de", "des", "du", "et", "un", "une", "pour", "avec",
        "facture", "total", "tva", "montant", "date", "client", "société", "siren",
    },
    LanguageCode.EN.value: {
        "the", "and", "of", "to", "in", "for", "invoice", "total", "amount",
        "date", "customer", "tax", "payment", "from",
    },
    LanguageCode.DE.value: {
        "der", "die", "das", "und", "für", "rechnung", "betrag", "datum", "mwst",
        "kunde", "mit", "von",
    },
    LanguageCode.ES.value: {
        "el", "la", "los", "las", "de", "y", "factura", "total", "fecha", "cliente",
        "importe", "con",
    },
    LanguageCode.IT.value: {
        "il", "la", "di", "e", "fattura", "totale", "data", "cliente", "importo",
        "con", "per",
    },
    LanguageCode.NL.value: {
        "de", "het", "een", "van", "en", "factuur", "totaal", "datum", "klant",
        "bedrag", "met",
    },
}


def _extract_sample_text(content: bytes, technical: dict[str, Any]) -> str:
    fmt = technical.get("detected_format")
    if fmt == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content), strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    return ""
            chunks: list[str] = []
            for page in reader.pages[:5]:
                try:
                    chunks.append(page.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(chunks)[:8000]
        except Exception:
            return ""
    if fmt in {"csv", "json", "xml", "txt"}:
        try:
            return content[:8000].decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return ""


def analyze_language(content: bytes, technical: dict[str, Any]) -> dict[str, Any]:
    text = _extract_sample_text(content, technical)
    if not text or len(text.strip()) < 20:
        # PDF scanné / image → unknown
        return {
            "code": LanguageCode.UNKNOWN.value,
            "confidence": 0.0,
            "sample_chars": len(text),
            "method": "insufficient_text",
        }
    tokens = re.findall(r"[A-Za-zÀ-ÿ]{2,}", text.lower())
    if not tokens:
        return {
            "code": LanguageCode.UNKNOWN.value,
            "confidence": 0.0,
            "sample_chars": len(text),
            "method": "no_tokens",
        }
    scores: dict[str, int] = {k: 0 for k in _STOPWORDS}
    for tok in tokens:
        for lang, words in _STOPWORDS.items():
            if tok in words:
                scores[lang] += 1
    best = max(scores.items(), key=lambda x: x[1])
    total_hits = sum(scores.values())
    if best[1] == 0 or total_hits == 0:
        return {
            "code": LanguageCode.UNKNOWN.value,
            "confidence": 0.1,
            "sample_chars": len(text),
            "method": "heuristic_stopwords",
            "scores": scores,
        }
    confidence = min(0.95, best[1] / max(8, total_hits) + 0.35)
    return {
        "code": best[0],
        "confidence": round(confidence, 3),
        "sample_chars": len(text),
        "method": "heuristic_stopwords",
        "scores": scores,
    }
