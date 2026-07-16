from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.elfis_ai.history import SupplierHistory, month_spend_for_org
from app.elfis_ai.schemas import ExtractionBlock, FinancialBlock, INSUFFICIENT_DATA
from app.models import Invoice


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("/", "-")
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def run_financial_agent(
    db: Session,
    invoice: Invoice,
    extraction: ExtractionBlock,
    history: SupplierHistory,
) -> FinancialBlock:
    messages: list[str] = []
    limitations = ""

    month_total, month_count = month_spend_for_org(
        db,
        organization_id=invoice.organization_id,
        invoice_date=invoice.invoice_date,
        exclude_invoice_id=None,  # inclure ce document dans le poids du mois
    )
    weight = None
    if invoice.amount_ttc is not None and month_total > 0:
        weight = round(float(invoice.amount_ttc) / month_total * 100, 1)
        messages.append(f"Cette dépense représente {weight} % des achats du mois ({month_count} document(s)).")

    due_field = extraction.document.get("due_date")
    due_raw = str(due_field.value) if due_field and due_field.value else None
    due = _parse_date(due_raw)
    issue = _parse_date(invoice.invoice_date)
    due_in_days = None
    recommended = due_raw
    if due:
        due_in_days = (due.date() - datetime.utcnow().date()).days
        if due_in_days >= 0:
            messages.append(f"Le règlement est prévu dans {due_in_days} jour(s).")
        else:
            messages.append(f"Échéance dépassée depuis {abs(due_in_days)} jour(s).")
    elif issue:
        recommended = (issue + timedelta(days=30)).strftime("%d-%m-%Y")
        messages.append(f"Aucune échéance détectée — échéance indicative à 30 jours : {recommended}.")
        limitations = "Échéance estimée faute de date explicite sur le document."

    vs_pct = None
    unusual = None
    avg = history.average_amount
    if history.document_count < 2 or avg is None:
        messages.append("Analyse comparative indisponible : historique insuffisant.")
        status = INSUFFICIENT_DATA
        if not limitations:
            limitations = "Historique fournisseur insuffisant pour une comparaison fiable."
    else:
        status = "ok"
        if invoice.amount_ttc is not None and avg > 0:
            vs_pct = round((float(invoice.amount_ttc) - avg) / avg * 100, 1)
            unusual = abs(vs_pct) >= 20
            direction = "supérieure" if vs_pct > 0 else "inférieure"
            messages.append(
                f"Cette facture est {direction} de {abs(vs_pct)} % au montant moyen de ce fournisseur "
                f"({avg:.2f} €)."
            )

    cash = None
    if invoice.amount_ttc is not None:
        cash = f"Impact trésorerie estimé : sortie de {float(invoice.amount_ttc):.2f} € à l'échéance."
        messages.append(cash)

    return FinancialBlock(
        status=status,
        monthly_weight_pct=weight,
        cash_impact=cash,
        recommended_payment_date=recommended,
        amount_remaining=float(invoice.amount_ttc) if invoice.amount_ttc is not None else None,
        due_in_days=due_in_days,
        supplier_avg_amount=avg,
        vs_supplier_avg_pct=vs_pct,
        unusual_amount=unusual,
        messages=messages,
        limitations=limitations,
    )
