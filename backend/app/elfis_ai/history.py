from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Invoice


def normalize_supplier(name: str | None) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"\s+", " ", name.strip().lower())
    return cleaned


@dataclass
class SupplierHistory:
    document_count: int
    amounts: list[float]
    dates: list[str]
    invoice_numbers: list[str]
    ibans: list[str]
    anomaly_count: int
    average_amount: float | None
    cumulative_amount: float | None
    last_date: str | None


def load_supplier_history(
    db: Session,
    *,
    organization_id: int,
    supplier: str | None,
    exclude_invoice_id: int | None = None,
) -> SupplierHistory:
    needle = normalize_supplier(supplier)
    empty = SupplierHistory(0, [], [], [], [], 0, None, None, None)
    if not needle:
        return empty

    rows = (
        db.query(Invoice)
        .filter(Invoice.organization_id == organization_id)
        .order_by(Invoice.id.desc())
        .limit(500)
        .all()
    )
    amounts: list[float] = []
    dates: list[str] = []
    numbers: list[str] = []
    ibans: list[str] = []
    anomaly_count = 0
    count = 0
    for inv in rows:
        if exclude_invoice_id and inv.id == exclude_invoice_id:
            continue
        if normalize_supplier(inv.supplier) != needle:
            continue
        count += 1
        if inv.amount_ttc is not None:
            amounts.append(float(inv.amount_ttc))
        if inv.invoice_date:
            dates.append(inv.invoice_date)
        if inv.invoice_number:
            numbers.append(inv.invoice_number.strip().upper())
        if inv.anomalies:
            try:
                anomaly_count += len(json.loads(inv.anomalies or "[]"))
            except json.JSONDecodeError:
                pass
        if inv.raw_extraction:
            try:
                raw = json.loads(inv.raw_extraction)
                iban = (raw.get("supplier_iban") or "").strip().upper()
                if iban and iban not in ibans:
                    ibans.append(iban)
            except json.JSONDecodeError:
                pass

    avg = round(sum(amounts) / len(amounts), 2) if amounts else None
    cumul = round(sum(amounts), 2) if amounts else None
    last = dates[0] if dates else None
    return SupplierHistory(
        document_count=count,
        amounts=amounts,
        dates=dates,
        invoice_numbers=numbers,
        ibans=ibans,
        anomaly_count=anomaly_count,
        average_amount=avg,
        cumulative_amount=cumul,
        last_date=last,
    )


def find_duplicate_candidates(
    db: Session,
    *,
    organization_id: int,
    invoice: Invoice,
) -> list[Invoice]:
    q = db.query(Invoice).filter(
        Invoice.organization_id == organization_id,
        Invoice.id != invoice.id,
    )
    matches: list[Invoice] = []
    number = (invoice.invoice_number or "").strip().upper()
    supplier = normalize_supplier(invoice.supplier)
    for other in q.limit(500).all():
        other_number = (other.invoice_number or "").strip().upper()
        other_supplier = normalize_supplier(other.supplier)
        if number and other_number and number == other_number and supplier and other_supplier == supplier:
            matches.append(other)
            continue
        if (
            invoice.amount_ttc is not None
            and other.amount_ttc is not None
            and abs(float(invoice.amount_ttc) - float(other.amount_ttc)) < 0.01
            and invoice.invoice_date
            and other.invoice_date
            and invoice.invoice_date == other.invoice_date
            and supplier
            and other_supplier == supplier
        ):
            matches.append(other)
    return matches


def month_spend_for_org(
    db: Session,
    *,
    organization_id: int,
    invoice_date: str | None,
    exclude_invoice_id: int | None = None,
) -> tuple[float, int]:
    """Retourne (total TTC mois, nb docs) pour le mois de la facture si date parseable."""
    if not invoice_date or len(invoice_date) < 7:
        return 0.0, 0
    # JJ-MM-AAAA
    parts = invoice_date.replace("/", "-").split("-")
    if len(parts) != 3:
        return 0.0, 0
    month, year = parts[1], parts[2]
    total = 0.0
    count = 0
    for inv in (
        db.query(Invoice)
        .filter(Invoice.organization_id == organization_id)
        .limit(1000)
        .all()
    ):
        if exclude_invoice_id and inv.id == exclude_invoice_id:
            continue
        d = (inv.invoice_date or "").replace("/", "-")
        dp = d.split("-")
        if len(dp) != 3:
            continue
        if dp[1] == month and dp[2] == year and inv.amount_ttc is not None:
            total += float(inv.amount_ttc)
            count += 1
    return round(total, 2), count
