from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.mapper import map_accounting
from app.agents.reader import read_document
from app.agents.validator import validate_financials
from app.models import CompanySettings, Invoice
from app.schemas import ExtractionResult


def get_or_create_settings(db: Session, organization_id: int = 0) -> CompanySettings:
    settings_row = (
        db.query(CompanySettings)
        .filter(CompanySettings.organization_id == organization_id)
        .first()
    )
    if not settings_row:
        settings_row = CompanySettings(organization_id=organization_id)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def _apply_pipeline_result(
    invoice: Invoice,
    extraction: ExtractionResult,
    company: CompanySettings,
) -> Invoice:
    validation = validate_financials(
        extraction,
        confidence_threshold=company.confidence_threshold,
        default_vat_rate=company.default_vat_rate,
    )
    entry = map_accounting(
        extraction,
        expense_account=company.expense_account,
        vat_account=company.vat_account,
        supplier_account=company.supplier_account,
    )

    invoice.supplier = extraction.supplier
    invoice.invoice_date = extraction.invoice_date
    invoice.invoice_number = extraction.invoice_number
    invoice.amount_ht = extraction.amount_ht
    invoice.amount_tva = extraction.amount_tva
    invoice.amount_ttc = extraction.amount_ttc
    invoice.vat_rate = extraction.vat_rate
    invoice.document_type = extraction.document_type
    invoice.confidence_score = extraction.confidence_score
    invoice.anomalies = json.dumps(validation.anomalies, ensure_ascii=False)
    invoice.missing_fields = json.dumps(validation.missing_fields, ensure_ascii=False)
    invoice.accounting_entry = entry.model_dump_json()
    invoice.raw_extraction = extraction.model_dump_json()
    invoice.needs_review = validation.needs_review
    invoice.status = "to_review" if validation.needs_review else "ready"
    return invoice


def invoice_to_extraction(invoice: Invoice) -> ExtractionResult:
    return ExtractionResult(
        supplier=invoice.supplier,
        invoice_date=invoice.invoice_date,
        invoice_number=invoice.invoice_number,
        amount_ht=invoice.amount_ht,
        amount_tva=invoice.amount_tva,
        amount_ttc=invoice.amount_ttc,
        vat_rate=invoice.vat_rate,
        document_type=invoice.document_type or "facture",
        confidence_score=invoice.confidence_score or 1.0,
        raw_text="",
    )


def _safe_elfis_analysis(db: Session, invoice: Invoice, extraction: ExtractionResult | None = None) -> None:
    """Analyse ELFIS AI post-pipeline : ne doit jamais faire échouer la facture."""
    try:
        from app.elfis_ai.orchestrator import run_elfis_analysis

        run_elfis_analysis(db, invoice, extraction=extraction)
    except Exception:
        # Conservé volontairement silencieux côté pipeline métier
        pass


def _safe_contact_suggestions(db: Session, invoice: Invoice) -> list[dict]:
    """Suggestions contacts : secondaire, ne doit jamais faire échouer le pipeline."""
    try:
        from app.services.contacts.detection_service import safe_generate_suggestions

        return safe_generate_suggestions(db, invoice)
    except Exception:
        return []


async def process_invoice(db: Session, invoice: Invoice) -> Invoice:
    company = get_or_create_settings(db, invoice.organization_id)
    path = Path(invoice.stored_path)
    extraction = await read_document(path, invoice.filename)
    _apply_pipeline_result(invoice, extraction, company)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    _safe_elfis_analysis(db, invoice, extraction)
    db.refresh(invoice)
    _safe_contact_suggestions(db, invoice)
    db.refresh(invoice)
    return invoice


def refresh_from_manual_edit(db: Session, invoice: Invoice) -> Invoice:
    """Revalide et régénère l'écriture après édition manuelle."""
    company = get_or_create_settings(db, invoice.organization_id)
    extraction = invoice_to_extraction(invoice)
    # Après correction humaine, on remonte légèrement la confiance si tout est rempli
    if all(
        [
            extraction.supplier,
            extraction.invoice_date,
            extraction.invoice_number,
            extraction.amount_ht is not None,
            extraction.amount_tva is not None,
            extraction.amount_ttc is not None,
        ]
    ):
        extraction.confidence_score = max(extraction.confidence_score, 0.95)
    _apply_pipeline_result(invoice, extraction, company)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    _safe_elfis_analysis(db, invoice, extraction)
    db.refresh(invoice)
    _safe_contact_suggestions(db, invoice)
    db.refresh(invoice)
    return invoice
