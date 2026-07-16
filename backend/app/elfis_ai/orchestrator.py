from __future__ import annotations

import json
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.pipeline import get_or_create_settings, invoice_to_extraction
from app.elfis_ai.agents.accounting import run_accounting_agent
from app.elfis_ai.agents.anomaly import run_anomaly_agent
from app.elfis_ai.agents.cfo import run_cfo_agent
from app.elfis_ai.agents.compliance import run_compliance_agent
from app.elfis_ai.agents.confidence import run_confidence_agent
from app.elfis_ai.agents.document_intelligence import run_document_intelligence
from app.elfis_ai.agents.financial import run_financial_agent
from app.elfis_ai.agents.fraud import run_fraud_agent
from app.elfis_ai.agents.recommendation import run_recommendation_agent
from app.elfis_ai.agents.supplier import run_supplier_agent
from app.elfis_ai.agents.tax import run_tax_agent
from app.elfis_ai.history import load_supplier_history
from app.elfis_ai.schemas import ANALYSIS_VERSION, AnalysisMetadata, ElfisReport
from app.models import ElfisAnalysis, Invoice
from app.schemas import ExtractionResult


def get_latest_analysis(db: Session, invoice_id: int, organization_id: int) -> ElfisAnalysis | None:
    return (
        db.query(ElfisAnalysis)
        .filter(
            ElfisAnalysis.invoice_id == invoice_id,
            ElfisAnalysis.organization_id == organization_id,
        )
        .order_by(ElfisAnalysis.id.desc())
        .first()
    )


def report_from_analysis(row: ElfisAnalysis) -> ElfisReport:
    data = json.loads(row.report_json or "{}")
    report = ElfisReport.model_validate(data)
    report.metadata.analysis_id = row.id
    report.metadata.created_at = row.created_at.isoformat() if row.created_at else None
    report.metadata.updated_at = row.updated_at.isoformat() if row.updated_at else None
    report.metadata.processing_time_ms = row.processing_time_ms
    report.metadata.status = row.status
    return report


def run_elfis_analysis(
    db: Session,
    invoice: Invoice,
    *,
    user_id: int | None = None,
    extraction: ExtractionResult | None = None,
) -> ElfisAnalysis:
    started = time.perf_counter()
    settings = get_or_create_settings(db, invoice.organization_id)
    ext = extraction or invoice_to_extraction(invoice)
    # Préserver champs enrichis depuis raw_extraction
    if invoice.raw_extraction:
        try:
            raw = json.loads(invoice.raw_extraction)
            ext = ExtractionResult.model_validate({**ext.model_dump(), **{
                k: v for k, v in raw.items() if v is not None
            }})
        except Exception:
            pass

    history = load_supplier_history(
        db,
        organization_id=invoice.organization_id,
        supplier=invoice.supplier,
        exclude_invoice_id=invoice.id,
    )

    extraction_block = run_document_intelligence(invoice, ext)
    accounting = run_accounting_agent(invoice, settings)
    checks = run_anomaly_agent(db, invoice, extraction_block)
    financial = run_financial_agent(db, invoice, extraction_block, history)
    supplier = run_supplier_agent(invoice, history)
    risk = run_fraud_agent(invoice, extraction_block, history, checks.anomalies)
    tax = run_tax_agent(invoice, extraction_block, accounting)
    compliance = run_compliance_agent(invoice, extraction_block)
    confidence = run_confidence_agent(invoice, extraction_block, accounting, checks.anomalies)
    recommendations = run_recommendation_agent(
        invoice, checks.anomalies, accounting, financial, risk, tax, compliance
    )
    cfo = run_cfo_agent(invoice, checks.anomalies, accounting, financial, risk, recommendations)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    summary_card = {
        "document_type": invoice.document_type or "facture",
        "amount_ttc": invoice.amount_ttc,
        "confidence": confidence.global_score,
        "confidence_pct": int(round(confidence.global_score * 100)),
        "status": invoice.status,
        "risk_level": risk.level,
        "anomaly_count": len(checks.anomalies),
        "blocking_anomaly_count": sum(1 for a in checks.anomalies if a.blocking),
        "fields_extracted": sum(
            1
            for block in (extraction_block.supplier, extraction_block.customer, extraction_block.document, extraction_block.totals)
            for field in block.values()
            if field.status == "found"
        ),
        "processing_time_ms": elapsed_ms,
        "accounting_balanced": accounting.balanced,
        "ready_label": (
            "Prêt à enregistrer"
            if invoice.status == "ready" and not any(a.blocking for a in checks.anomalies)
            else "À vérifier"
        ),
    }

    report = ElfisReport(
        metadata=AnalysisMetadata(
            document_id=invoice.id,
            organization_id=invoice.organization_id,
            user_id=user_id,
            analysis_version=ANALYSIS_VERSION,
            processing_time_ms=elapsed_ms,
            status="completed",
            created_at=datetime.utcnow().isoformat(),
        ),
        extraction=extraction_block,
        confidence=confidence,
        accounting=accounting,
        checks=checks,
        financial_analysis=financial,
        risk_analysis=risk,
        tax_analysis=tax,
        compliance=compliance,
        supplier_intelligence=supplier,
        recommendations=recommendations,
        cfo_summary=cfo,
        summary_card=summary_card,
    )

    row = ElfisAnalysis(
        invoice_id=invoice.id,
        organization_id=invoice.organization_id,
        user_id=user_id,
        status="completed",
        analysis_version=ANALYSIS_VERSION,
        processing_time_ms=elapsed_ms,
        report_json=report.model_dump_json(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
