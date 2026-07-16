from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.elfis_ai.orchestrator import get_latest_analysis, report_from_analysis
from app.models import Invoice
from app.models_saas import SalesDocument

Period = Literal["month", "previous_month", "quarter", "year"]


def _period_bounds(period: Period) -> tuple[datetime, datetime, str]:
    now = datetime.utcnow()
    if period == "previous_month":
        first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = first_this
        label = "mois précédent"
    elif period == "quarter":
        q = (now.month - 1) // 3
        start = now.replace(month=q * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        label = "trimestre"
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        label = "année"
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        label = "ce mois"
    return start, end, label


def _in_period(invoice: Invoice, start: datetime, end: datetime) -> bool:
    if invoice.created_at and start <= invoice.created_at <= end:
        return True
    # fallback date document JJ-MM-AAAA
    d = (invoice.invoice_date or "").replace("/", "-")
    parts = d.split("-")
    if len(parts) != 3:
        return False
    try:
        parsed = datetime.strptime(d, "%d-%m-%Y")
    except ValueError:
        return False
    return start.date() <= parsed.date() <= end.date()


def build_intelligence_overview(db: Session, organization_id: int, period: Period = "month") -> dict:
    start, end, label = _period_bounds(period)
    invoices = (
        db.query(Invoice)
        .filter(Invoice.organization_id == organization_id)
        .order_by(Invoice.id.desc())
        .limit(1000)
        .all()
    )
    period_invoices = [i for i in invoices if _in_period(i, start, end)]
    expenses = round(sum(float(i.amount_ttc or 0) for i in period_invoices), 2)
    vat = round(sum(float(i.amount_tva or 0) for i in period_invoices), 2)
    to_review = sum(1 for i in period_invoices if i.needs_review or i.status == "to_review")

    sales = (
        db.query(SalesDocument)
        .filter(SalesDocument.organization_id == organization_id)
        .all()
    )
    client_unpaid = [
        d
        for d in sales
        if d.doc_type == "facture" and d.status in ("sent", "partial", "overdue")
    ]
    ca = round(sum(float(d.amount_ttc or 0) for d in sales if d.doc_type == "facture" and d.status == "paid"), 2)
    client_pending = round(sum(float(d.amount_ttc - d.paid_amount) for d in client_unpaid), 2)

    alerts: list[dict] = []
    opportunities: list[dict] = []
    anomalies_open: list[dict] = []

    for inv in invoices[:80]:
        analysis = get_latest_analysis(db, inv.id, organization_id)
        if not analysis:
            continue
        try:
            report = report_from_analysis(analysis)
        except Exception:
            continue
        for anomaly in report.checks.anomalies:
            if anomaly.blocking or anomaly.severity in ("elevee", "critique"):
                item = {
                    "type": anomaly.category,
                    "priority": "haute" if anomaly.blocking else "moyenne",
                    "title": anomaly.title,
                    "description": anomaly.description,
                    "document_id": inv.id,
                    "document_label": inv.invoice_number or inv.filename,
                }
                alerts.append(item)
                anomalies_open.append(item)
        if report.risk_analysis.level in ("eleve", "critique"):
            alerts.append(
                {
                    "type": "risque",
                    "priority": "haute",
                    "title": "Risque potentiel détecté",
                    "description": report.risk_analysis.recommendation,
                    "document_id": inv.id,
                    "document_label": inv.invoice_number or inv.filename,
                }
            )
        if report.financial_analysis.unusual_amount:
            opportunities.append(
                {
                    "type": "hausse_prix",
                    "title": "Montant inhabituel fournisseur",
                    "description": "; ".join(report.financial_analysis.messages[:2]),
                    "document_id": inv.id,
                }
            )
        if report.risk_analysis.factors:
            for factor in report.risk_analysis.factors:
                if factor.code == "iban_change":
                    alerts.append(
                        {
                            "type": "nouvel_iban",
                            "priority": "haute",
                            "title": "Nouvel IBAN",
                            "description": factor.detail,
                            "document_id": inv.id,
                            "document_label": inv.invoice_number or inv.filename,
                        }
                    )

    for d in client_unpaid[:20]:
        alerts.append(
            {
                "type": "facture_client",
                "priority": "moyenne",
                "title": f"Facture client en attente {d.number}",
                "description": f"{d.customer_name} — {d.amount_ttc - d.paid_amount:.2f} € restant",
                "document_id": None,
                "sales_document_id": d.id,
                "document_label": d.number,
            }
        )
        opportunities.append(
            {
                "type": "relance_client",
                "title": f"Relancer {d.customer_name}",
                "description": f"Facture {d.number} encore ouverte.",
                "sales_document_id": d.id,
            }
        )

    # Prévisions prudentes
    due_outflows = 0.0
    due_count = 0
    for inv in invoices:
        analysis = get_latest_analysis(db, inv.id, organization_id)
        if not analysis:
            continue
        try:
            report = report_from_analysis(analysis)
        except Exception:
            continue
        days = report.financial_analysis.due_in_days
        if days is not None and 0 <= days <= 30 and inv.amount_ttc is not None:
            due_outflows += float(inv.amount_ttc)
            due_count += 1

    forecasts = {
        "status": "ok" if due_count >= 1 or client_pending > 0 else "insufficient_data",
        "outflows_30d": round(due_outflows, 2) if due_count else None,
        "inflows_expected": client_pending if client_unpaid else None,
        "vat_estimate": vat,
        "method": (
            "Prévision calculée à partir des factures et échéances enregistrées. "
            "Les mouvements bancaires non intégrés ne sont pas pris en compte."
        ),
        "limitations": (
            "Données insuffisantes pour une prévision robuste."
            if due_count < 1 and not client_unpaid
            else ""
        ),
    }

    recent = [
        {
            "id": i.id,
            "supplier": i.supplier,
            "number": i.invoice_number,
            "amount_ttc": i.amount_ttc,
            "status": i.status,
            "date": i.invoice_date,
            "needs_review": i.needs_review,
        }
        for i in period_invoices[:12]
    ]

    resultat = None
    if ca or expenses:
        resultat = round(ca - expenses, 2)

    return {
        "period": period,
        "period_label": label,
        "company_synthesis": {
            "revenue": ca if ca else None,
            "expenses": expenses,
            "estimated_result": resultat,
            "estimated_vat": vat,
            "client_invoices_pending": len(client_unpaid),
            "client_amount_pending": client_pending,
            "supplier_invoices_to_pay": len([i for i in period_invoices if i.status in ("ready", "to_review")]),
            "supplier_amount": expenses,
            "treasury": "not_available",
            "documents_analyzed": len(period_invoices),
            "open_anomalies": len(anomalies_open),
        },
        "alerts": alerts[:30],
        "recent_activity": recent,
        "anomalies": anomalies_open[:30],
        "forecasts": forecasts,
        "opportunities": opportunities[:20],
        "generated_at": datetime.utcnow().isoformat(),
    }
