from __future__ import annotations

import json

from app.models import Invoice
from app.schemas import AccountingEntry, InvoiceOut


def serialize_invoice(invoice: Invoice) -> InvoiceOut:
    anomalies = json.loads(invoice.anomalies or "[]")
    missing = json.loads(invoice.missing_fields or "[]")
    entry = None
    if invoice.accounting_entry:
        try:
            entry = AccountingEntry.model_validate_json(invoice.accounting_entry)
        except Exception:
            entry = None
    return InvoiceOut(
        id=invoice.id,
        filename=invoice.filename,
        mime_type=invoice.mime_type,
        supplier=invoice.supplier,
        invoice_date=invoice.invoice_date,
        invoice_number=invoice.invoice_number,
        amount_ht=invoice.amount_ht,
        amount_tva=invoice.amount_tva,
        amount_ttc=invoice.amount_ttc,
        vat_rate=invoice.vat_rate,
        document_type=invoice.document_type,
        confidence_score=invoice.confidence_score,
        status=invoice.status,
        needs_review=invoice.needs_review,
        anomalies=anomalies,
        missing_fields=missing,
        accounting_entry=entry,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )