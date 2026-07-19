from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Invoice
from app.schemas import AccountingEntry, InvoiceOut


def serialize_invoice(
    invoice: Invoice,
    *,
    db: Session | None = None,
    include_contact_suggestions: bool = False,
) -> InvoiceOut:
    anomalies = json.loads(invoice.anomalies or "[]")
    missing = json.loads(invoice.missing_fields or "[]")
    entry = None
    if invoice.accounting_entry:
        try:
            entry = AccountingEntry.model_validate_json(invoice.accounting_entry)
        except Exception:
            entry = None
    suggestions: list[dict] = []
    if include_contact_suggestions and db is not None:
        try:
            from app.services.contacts.detection_service import list_pending_suggestions

            suggestions = list_pending_suggestions(
                db,
                document_id=invoice.id,
                organization_id=invoice.organization_id,
            )
        except Exception:
            suggestions = []
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
        supplier_contact_id=getattr(invoice, "supplier_contact_id", None),
        customer_contact_id=getattr(invoice, "customer_contact_id", None),
        contact_suggestions=suggestions,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )