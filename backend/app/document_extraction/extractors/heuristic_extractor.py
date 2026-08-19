"""Extracteur heuristique — regex / patterns (pas de LLM)."""

from __future__ import annotations

import re
from typing import Any

from app.document_extraction.enums import FieldSource

_DATE = re.compile(
    r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
)
_AMOUNT = re.compile(
    r"(?:total|ttc|montant|amount|total ttc)[^\d]{0,20}([0-9]{1,3}(?:[ .]?[0-9]{3})*[.,][0-9]{2})",
    re.I,
)
_HT = re.compile(
    r"(?:ht|hors tax|subtotal|hors tva)[^\d]{0,20}([0-9]{1,3}(?:[ .]?[0-9]{3})*[.,][0-9]{2})",
    re.I,
)
_TVA = re.compile(
    r"(?:tva|vat|tax)[^\d]{0,20}([0-9]{1,3}(?:[ .]?[0-9]{3})*[.,][0-9]{2})",
    re.I,
)
_INVOICE_NO = re.compile(
    r"(?:facture|invoice|n[°o]|number)[^\w]{0,10}([A-Z0-9][A-Z0-9\-/]{3,})",
    re.I,
)
_SIRET = re.compile(r"\b(\d{14})\b")
_SIREN = re.compile(r"\b(\d{9})\b")
_VAT = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{8,12})\b")
_IBAN = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{10,30})\b")
_CURRENCY = re.compile(r"\b(EUR|USD|GBP|CHF)\b", re.I)


def _prov(path: str, value: Any, raw: Any, confidence: float) -> dict[str, Any]:
    return {
        "field_path": path,
        "value": value,
        "raw_value": raw,
        "source": FieldSource.HEURISTIC.value,
        "page_number": None,
        "text_span": None,
        "bounding_box": None,
        "extractor_name": "heuristic_extractor",
        "extractor_version": "1.0",
        "confidence": confidence,
        "warnings": [],
    }


def extract_heuristic(
    text: str,
    *,
    document_type: str,
    filename: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retourne (structured_data, provenance)."""
    data: dict[str, Any] = {}
    provenance: dict[str, Any] = {}

    m = _INVOICE_NO.search(text) or _INVOICE_NO.search(filename)
    if m:
        key = {
            "invoice": "document_number",
            "quote": "quote_number",
            "credit_note": "credit_note_number",
            "receipt": "receipt_number",
        }.get(document_type, "document_number")
        data[key] = m.group(1)
        provenance[key] = _prov(key, m.group(1), m.group(0), 0.75)

    dm = _DATE.search(text)
    if dm:
        date_key = {
            "quote": "issue_date",
            "credit_note": "credit_note_date",
        }.get(document_type, "document_date")
        data[date_key] = dm.group(1)
        provenance[date_key] = _prov(date_key, dm.group(1), dm.group(0), 0.7)

    amounts: dict[str, Any] = {}
    for label, pat, conf in (
        ("total_including_tax", _AMOUNT, 0.8),
        ("subtotal_excluding_tax", _HT, 0.7),
        ("total_tax", _TVA, 0.7),
    ):
        am = pat.search(text)
        if am:
            amounts[label] = am.group(1)
            path = f"amounts.{label}"
            provenance[path] = _prov(path, am.group(1), am.group(0), conf)
    if amounts:
        data["amounts"] = amounts

    cur = _CURRENCY.search(text)
    if cur:
        data["currency"] = cur.group(1).upper()
        provenance["currency"] = _prov("currency", data["currency"], cur.group(0), 0.85)
    elif "€" in text:
        data["currency"] = "EUR"
        provenance["currency"] = _prov("currency", "EUR", "€", 0.8)

    supplier: dict[str, Any] = {}
    siret = _SIRET.search(text)
    if siret:
        supplier["registration_number"] = siret.group(1)
        provenance["supplier.registration_number"] = _prov(
            "supplier.registration_number", siret.group(1), siret.group(0), 0.85
        )
    vat = _VAT.search(text)
    if vat:
        supplier["vat_number"] = vat.group(1)
        provenance["supplier.vat_number"] = _prov(
            "supplier.vat_number", vat.group(1), vat.group(0), 0.8
        )
    iban = _IBAN.search(text)
    if iban and document_type != "bank_statement":
        raw_iban = iban.group(1)
        supplier["iban"] = raw_iban
        provenance["supplier.iban"] = _prov("supplier.iban", raw_iban, raw_iban, 0.75)
    if "facture" in text.lower() or "invoice" in filename.lower():
        # nom fournisseur approximatif : première ligne non vide
        for line in text.splitlines()[:8]:
            line = line.strip()
            if len(line) > 3 and not line.lower().startswith(("facture", "invoice", "page")):
                supplier["name"] = line[:120]
                provenance["supplier.name"] = _prov("supplier.name", line[:120], line, 0.55)
                break
    if supplier:
        if document_type == "receipt":
            data["merchant_name"] = supplier.get("name")
            if data.get("merchant_name"):
                provenance["merchant_name"] = provenance.get("supplier.name", {})
        else:
            data["supplier"] = supplier

    if document_type == "bank_statement":
        data.setdefault("transactions", [])
        if iban:
            masked = iban.group(1)[:4] + "****" + iban.group(1)[-4:]
            data["iban_masked"] = masked
            provenance["iban_masked"] = _prov("iban_masked", masked, "IBAN", 0.8)

    if document_type == "contract":
        data.setdefault("parties", [])
        data.setdefault("key_clauses", [])
        if not data.get("contract_title"):
            data["contract_title"] = filename[:120]

    return data, provenance
