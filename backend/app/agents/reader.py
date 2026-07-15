from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import settings
from app.schemas import ExtractionResult
from app.services.ocr import detect_document_type, extract_text_from_file


def _find_labeled_amount(text: str, labels: list[str]) -> float | None:
    for label in labels:
        pattern = rf"{label}\s*[:\-]?\s*(\d+[.,]\d{{2}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def _find_supplier(text: str) -> str | None:
    patterns = [
        r"(?:soci[eé]t[eé]|sarl|sas|eurl|sasu|sa)\s+([A-ZÀ-Ü][A-Za-zÀ-ÿ0-9 &\-]{2,40})",
        r"(?:fournisseur|vendeur|émetteur|emetteur)\s*[:\-]?\s*([A-ZÀ-Ü][A-Za-zÀ-ÿ0-9 &\-]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _find_invoice_number(text: str) -> str | None:
    for pattern in [
        r"\b(FAC[-/\s]?\d[\w\-/]*)\b",
        r"(?:n[°o]|no|num(?:[eé]ro)?)\s*(?:de\s+facture)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{3,})",
        r"(?:facture|invoice)\s*(?:n[°o]|no)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{3,})",
    ]:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return re.sub(r"\s+", "", match.group(1)).upper()
    return None


def _heuristic_extraction(filename: str, text: str, engine: str) -> ExtractionResult:
    body = text or ""
    ht = _find_labeled_amount(body, [r"montant\s*h\.?\s*t\.?", r"\bht\b", r"hors\s*taxe"])
    tva = _find_labeled_amount(body, [r"montant\s*tva", r"\btva\b"])
    ttc = _find_labeled_amount(body, [r"montant\s*ttc", r"total\s*ttc", r"\bttc\b", r"net\s*[àa]\s*payer"])

    if ht is not None and tva is not None and ttc is None:
        ttc = round(ht + tva, 2)
    elif ht is not None and ttc is not None and tva is None:
        tva = round(ttc - ht, 2)
    elif tva is not None and ttc is not None and ht is None:
        ht = round(ttc - tva, 2)

    rate = round((tva / ht) * 100, 1) if ht and tva is not None else None
    date_match = re.search(r"(\d{2}[/-]\d{2}[/-]\d{4})", body)
    doc_type = detect_document_type(body, filename)

    if engine == "image-fallback":
        confidence = 0.25
    elif body and len(body) > 80:
        confidence = 0.7
    else:
        confidence = 0.35

    return ExtractionResult(
        supplier=_find_supplier(body),
        invoice_date=date_match.group(1).replace("/", "-") if date_match else None,
        invoice_number=_find_invoice_number(body),
        amount_ht=ht,
        amount_tva=tva,
        amount_ttc=ttc,
        vat_rate=rate,
        document_type=doc_type,
        confidence_score=confidence,
        raw_text=body[:4000] if body else f"Document: {filename}",
    )


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _structured_extract(text: str, filename: str) -> ExtractionResult:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""Tu es Document Reader, agent ELFIS Core — Module Comptabilité.
Extrais les champs d'un document fournisseur français.
Retourne UNIQUEMENT un JSON valide avec:
supplier, invoice_date (JJ-MM-AAAA), invoice_number, amount_ht, amount_tva, amount_ttc,
vat_rate, document_type (facture|avoir|devis|ticket|note_frais|releve|autre),
confidence_score (0-1), raw_text (résumé court).

Texte OCR:
{text[:8000]}
Fichier: {filename}
"""
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {"role": "system", "content": "Tu extrais des documents comptables. JSON strict."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    doc_type = data.get("document_type") or detect_document_type(text, filename)
    return ExtractionResult(
        supplier=data.get("supplier"),
        invoice_date=data.get("invoice_date"),
        invoice_number=data.get("invoice_number"),
        amount_ht=_to_float(data.get("amount_ht")),
        amount_tva=_to_float(data.get("amount_tva")),
        amount_ttc=_to_float(data.get("amount_ttc")),
        vat_rate=_to_float(data.get("vat_rate")),
        document_type=doc_type,
        confidence_score=_to_float(data.get("confidence_score")) or 0.7,
        raw_text=data.get("raw_text") or text[:2000],
    )


async def read_document(path: Path, filename: str) -> ExtractionResult:
    text, engine = extract_text_from_file(path)

    if settings.openai_api_key and text and engine != "image-fallback":
        try:
            return _structured_extract(text, filename)
        except Exception:
            return _heuristic_extraction(filename, text, engine)

    return _heuristic_extraction(filename, text, engine)
