from __future__ import annotations

import json

from app.elfis_ai.schemas import (
    NOT_AVAILABLE,
    ExtractionBlock,
    FieldValue,
    LineItemReport,
)
from app.models import Invoice
from app.schemas import ExtractionResult, LineItemExtraction


def _fv(value, *, confidence: float, source: str = "extraction") -> FieldValue:
    if value is None or value == "" or value == []:
        return FieldValue(value=None, confidence=0.0, source=source, status="not_available")
    status = "found" if confidence >= 0.6 else "uncertain"
    return FieldValue(value=value, confidence=round(confidence, 3), source=source, status=status)


def _load_raw(invoice: Invoice) -> dict:
    if not invoice.raw_extraction:
        return {}
    try:
        return json.loads(invoice.raw_extraction)
    except json.JSONDecodeError:
        return {}


def run_document_intelligence(invoice: Invoice, extraction: ExtractionResult | None = None) -> ExtractionBlock:
    raw = _load_raw(invoice)
    if invoice.confidence_score is not None:
        conf = float(invoice.confidence_score)
    elif extraction is not None:
        conf = float(extraction.confidence_score or 0.5)
    else:
        conf = 0.5
    conf = conf or 0.5

    def pick(*keys, fallback=None):
        for key in keys:
            if extraction and hasattr(extraction, key):
                val = getattr(extraction, key)
                if val not in (None, "", []):
                    return val
            if key in raw and raw[key] not in (None, "", []):
                return raw[key]
        return fallback

    supplier = {
        "name": _fv(invoice.supplier or pick("supplier"), confidence=conf),
        "address": _fv(pick("supplier_address"), confidence=conf * 0.85),
        "postal_code": _fv(None, confidence=0),
        "city": _fv(None, confidence=0),
        "country": _fv(None, confidence=0),
        "siret": _fv(pick("supplier_siret"), confidence=conf * 0.9),
        "siren": _fv(pick("supplier_siren"), confidence=conf * 0.9),
        "vat_number": _fv(pick("supplier_vat"), confidence=conf * 0.9),
        "phone": _fv(pick("supplier_phone"), confidence=conf * 0.7),
        "email": _fv(pick("supplier_email"), confidence=conf * 0.7),
        "website": _fv(None, confidence=0),
        "iban": _fv(pick("supplier_iban"), confidence=conf * 0.8),
        "bic": _fv(pick("supplier_bic"), confidence=conf * 0.8),
    }

    customer = {
        "name": _fv(pick("customer_name"), confidence=conf * 0.75),
        "address": _fv(pick("customer_address"), confidence=conf * 0.7),
        "postal_code": _fv(None, confidence=0),
        "city": _fv(None, confidence=0),
        "country": _fv(None, confidence=0),
        "siret": _fv(pick("customer_siret"), confidence=conf * 0.7),
        "vat_number": _fv(pick("customer_vat"), confidence=conf * 0.7),
        "phone": _fv(None, confidence=0),
        "email": _fv(None, confidence=0),
    }

    document = {
        "type": _fv(invoice.document_type or pick("document_type", fallback="facture"), confidence=conf),
        "number": _fv(invoice.invoice_number or pick("invoice_number"), confidence=conf),
        "issue_date": _fv(invoice.invoice_date or pick("invoice_date"), confidence=conf),
        "due_date": _fv(pick("due_date"), confidence=conf * 0.75),
        "currency": _fv(pick("currency", fallback="EUR"), confidence=0.9 if pick("currency") else 0.4),
        "payment_terms": _fv(pick("payment_terms"), confidence=conf * 0.6),
        "payment_method": _fv(pick("payment_method"), confidence=conf * 0.6),
        "order_reference": _fv(pick("order_reference"), confidence=conf * 0.6),
        "customer_reference": _fv(None, confidence=0),
        "billing_period": _fv(None, confidence=0),
        "amount_already_paid": _fv(None, confidence=0),
        "amount_remaining": _fv(invoice.amount_ttc, confidence=conf if invoice.amount_ttc is not None else 0),
    }

    totals = {
        "subtotal_ht": _fv(invoice.amount_ht, confidence=conf if invoice.amount_ht is not None else 0),
        "discounts": _fv(None, confidence=0),
        "fees": _fv(None, confidence=0),
        "total_ht": _fv(invoice.amount_ht, confidence=conf if invoice.amount_ht is not None else 0),
        "total_vat": _fv(invoice.amount_tva, confidence=conf if invoice.amount_tva is not None else 0),
        "total_ttc": _fv(invoice.amount_ttc, confidence=conf if invoice.amount_ttc is not None else 0),
        "deposit": _fv(None, confidence=0),
        "net_payable": _fv(invoice.amount_ttc, confidence=conf if invoice.amount_ttc is not None else 0),
        "vat_rate": _fv(invoice.vat_rate, confidence=conf if invoice.vat_rate is not None else 0),
    }

    legal = {
        "late_penalties": _fv(pick("late_penalty_mention"), confidence=0.5),
        "recovery_indemnity": _fv(pick("recovery_indemnity_mention"), confidence=0.5),
        "discount": _fv(None, confidence=0),
        "vat_exemption": _fv(pick("vat_exemption_mention"), confidence=0.5),
        "reverse_charge": _fv(pick("reverse_charge_mention"), confidence=0.5),
        "special_mentions": _fv(None, confidence=0),
    }

    lines_raw = pick("line_items", fallback=[]) or []
    line_items: list[LineItemReport] = []
    if isinstance(lines_raw, list):
        for item in lines_raw:
            if isinstance(item, LineItemExtraction):
                data = item.model_dump()
            elif isinstance(item, dict):
                data = item
            else:
                continue
            line_items.append(
                LineItemReport(
                    label=data.get("label") or data.get("description"),
                    description=data.get("description"),
                    reference=data.get("reference"),
                    quantity=data.get("quantity"),
                    unit=data.get("unit"),
                    unit_price_ht=data.get("unit_price_ht"),
                    discount=data.get("discount"),
                    vat_rate=data.get("vat_rate"),
                    vat_amount=data.get("vat_amount"),
                    total_ht=data.get("total_ht"),
                    total_ttc=data.get("total_ttc"),
                )
            )

    # Marquer explicitement l'absence de lignes
    if not line_items:
        document["line_items_status"] = FieldValue(
            value=NOT_AVAILABLE,
            confidence=0.0,
            source="system",
            status="not_available",
            anomaly="Aucune ligne détaillée extraite",
        )

    return ExtractionBlock(
        supplier=supplier,
        customer=customer,
        document=document,
        line_items=line_items,
        totals=totals,
        legal_mentions=legal,
    )
