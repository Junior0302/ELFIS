"""Adaptateur extraction AI / historique → ExtractionResult."""

from __future__ import annotations

from typing import Any

from app.schemas import ExtractionResult


def extraction_from_analysis(
    extraction_json: dict[str, Any] | None,
    *,
    document_type: str | None = None,
    confidence: float | None = None,
) -> ExtractionResult:
    """
    Accepte :
    - compatible_extraction (ExtractionResult dump)
    - structure AI (supplier/invoice/amounts)
    - ExtractionResult plat
    """
    data = extraction_json if isinstance(extraction_json, dict) else {}

    if "compatible_extraction" in data and isinstance(data["compatible_extraction"], dict):
        data = data["compatible_extraction"]

    nested = (
        isinstance(data.get("amounts"), dict)
        or isinstance(data.get("invoice"), dict)
        or isinstance(data.get("supplier"), dict)
        or isinstance(data.get("customer"), dict)
    )
    if nested:
        supplier = data.get("supplier") if isinstance(data.get("supplier"), dict) else {}
        customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
        invoice = data.get("invoice") if isinstance(data.get("invoice"), dict) else {}
        amounts = data.get("amounts") if isinstance(data.get("amounts"), dict) else {}
        return ExtractionResult(
            supplier=supplier.get("name") or (data.get("supplier") if isinstance(data.get("supplier"), str) else None) or data.get("supplier_name"),
            customer_name=customer.get("name") or data.get("customer_name"),
            invoice_number=invoice.get("number") or data.get("invoice_number"),
            invoice_date=invoice.get("date") or data.get("invoice_date"),
            due_date=invoice.get("due_date") or data.get("due_date"),
            currency=invoice.get("currency") or data.get("currency") or "EUR",
            amount_ht=_f(amounts.get("amount_ht", data.get("amount_ht"))),
            amount_tva=_f(amounts.get("amount_tva", amounts.get("amount_vat", data.get("amount_tva")))),
            amount_ttc=_f(amounts.get("amount_ttc", data.get("amount_ttc"))),
            vat_rate=_f(amounts.get("vat_rate", data.get("vat_rate"))),
            document_type=str(
                invoice.get("document_type")
                or data.get("document_type")
                or document_type
                or "facture"
            ),
            confidence_score=float(
                data.get("confidence")
                or data.get("confidence_score")
                or confidence
                or 0.0
            ),
            raw_text="",
        )

    payload = dict(data)
    if document_type and not payload.get("document_type"):
        payload["document_type"] = document_type
    if confidence is not None and payload.get("confidence_score") is None:
        payload["confidence_score"] = confidence
    # amount_vat alias
    if payload.get("amount_tva") is None and payload.get("amount_vat") is not None:
        payload["amount_tva"] = payload.get("amount_vat")
    return ExtractionResult.model_validate(payload)


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
