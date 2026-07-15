from __future__ import annotations

import csv
import io
from datetime import datetime

from app.models import Invoice
from app.schemas import AccountingEntry

SOFTWARE_TARGETS = ("fec", "sage", "pennylane", "cegid", "ebp", "odoo", "csv")


def _entry(invoice: Invoice) -> AccountingEntry | None:
    if not invoice.accounting_entry:
        return None
    try:
        return AccountingEntry.model_validate_json(invoice.accounting_entry)
    except Exception:
        return None


def _fmt_amount(value: float, decimal_comma: bool = True) -> str:
    text = f"{value:.2f}"
    return text.replace(".", ",") if decimal_comma else text


def _piece_date(invoice: Invoice, entry: AccountingEntry | None) -> str:
    if entry and entry.piece_date:
        return entry.piece_date
    raw = (invoice.invoice_date or "").replace("-", "").replace("/", "")
    if len(raw) == 8 and raw.isdigit():
        # JJMMYYYY → YYYYMMDD if starts with day
        if int(raw[4:6]) <= 12:
            return raw[4:8] + raw[2:4] + raw[0:2] if False else raw
    # try JJ-MM-YYYY
    parts = (invoice.invoice_date or "").replace("/", "-").split("-")
    if len(parts) == 3 and len(parts[2]) == 4:
        return f"{parts[2]}{parts[1]}{parts[0]}"
    return datetime.utcnow().strftime("%Y%m%d")


def invoices_to_fec(invoices: list[Invoice]) -> bytes:
    """Fichier des Écritures Comptables (DGFiP) — séparateur |."""
    headers = [
        "JournalCode",
        "JournalLib",
        "EcritureNum",
        "EcritureDate",
        "CompteNum",
        "CompteLib",
        "CompAuxNum",
        "CompAuxLib",
        "PieceRef",
        "PieceDate",
        "EcritureLib",
        "Debit",
        "Credit",
        "EcritureLet",
        "DateLet",
        "ValidDate",
        "Montantdevise",
        "Idevise",
    ]
    lines_out = ["|".join(headers)]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        ecriture_num = f"CP{invoice.id:06d}"
        ecriture_date = _piece_date(invoice, entry)
        piece_ref = entry.piece_ref or invoice.invoice_number or f"INV{invoice.id}"
        piece_date = entry.piece_date or ecriture_date
        for line in entry.lines:
            aux_num = ""
            aux_lib = ""
            if line.account.startswith("401"):
                aux_num = f"F{invoice.id:05d}"
                aux_lib = invoice.supplier or ""
            row = [
                entry.journal or "ACH",
                entry.journal_lib or "Achats",
                ecriture_num,
                ecriture_date,
                line.account,
                line.label[:50],
                aux_num,
                aux_lib,
                piece_ref,
                piece_date,
                entry.label[:80],
                _fmt_amount(line.debit) if line.debit else "0,00",
                _fmt_amount(line.credit) if line.credit else "0,00",
                "",
                "",
                ecriture_date,
                "",
                "",
            ]
            lines_out.append("|".join(row))
    # BOM UTF-8 pour Excel FR
    return ("\ufeff" + "\n".join(lines_out) + "\n").encode("utf-8")


def _csv_bytes(rows: list[list[str]], delimiter: str = ";") -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def invoices_to_sage(invoices: list[Invoice]) -> bytes:
    rows = [["Journal", "Date", "Compte", "Libellé", "Pièce", "Débit", "Crédit"]]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        date = invoice.invoice_date or ""
        for line in entry.lines:
            rows.append(
                [
                    entry.journal,
                    date,
                    line.account,
                    line.label,
                    entry.piece_ref or invoice.invoice_number or "",
                    _fmt_amount(line.debit),
                    _fmt_amount(line.credit),
                ]
            )
    return _csv_bytes(rows)


def invoices_to_pennylane(invoices: list[Invoice]) -> bytes:
    rows = [
        [
            "date",
            "journal_code",
            "label",
            "account_number",
            "debit",
            "credit",
            "invoice_number",
            "currency",
        ]
    ]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        for line in entry.lines:
            rows.append(
                [
                    invoice.invoice_date or "",
                    entry.journal,
                    entry.label,
                    line.account,
                    _fmt_amount(line.debit, decimal_comma=False),
                    _fmt_amount(line.credit, decimal_comma=False),
                    invoice.invoice_number or "",
                    "EUR",
                ]
            )
    return _csv_bytes(rows, delimiter=",")


def invoices_to_cegid(invoices: list[Invoice]) -> bytes:
    rows = [["Code journal", "Date écriture", "N° compte", "Libellé", "Réf pièce", "Débit", "Crédit", "Sens"]]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        for line in entry.lines:
            sens = "D" if line.debit else "C"
            montant = line.debit or line.credit
            rows.append(
                [
                    entry.journal,
                    invoice.invoice_date or "",
                    line.account,
                    line.label,
                    entry.piece_ref or "",
                    _fmt_amount(line.debit),
                    _fmt_amount(line.credit),
                    sens,
                ]
            )
    return _csv_bytes(rows)


def invoices_to_ebp(invoices: list[Invoice]) -> bytes:
    rows = [["Journal", "Date", "Compte général", "Compte tiers", "Libellé", "N° pièce", "Débit", "Crédit"]]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        tier = f"F{invoice.id:05d}" if invoice.supplier else ""
        for line in entry.lines:
            rows.append(
                [
                    entry.journal,
                    invoice.invoice_date or "",
                    line.account,
                    tier if line.account.startswith("401") else "",
                    line.label,
                    entry.piece_ref or invoice.invoice_number or "",
                    _fmt_amount(line.debit),
                    _fmt_amount(line.credit),
                ]
            )
    return _csv_bytes(rows)


def invoices_to_odoo(invoices: list[Invoice]) -> bytes:
    rows = [
        [
            "Journal",
            "Date",
            "Reference",
            "Partner",
            "Account",
            "Label",
            "Debit",
            "Credit",
        ]
    ]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        for line in entry.lines:
            rows.append(
                [
                    entry.journal,
                    invoice.invoice_date or "",
                    entry.piece_ref or invoice.invoice_number or "",
                    invoice.supplier or "",
                    line.account,
                    line.label,
                    _fmt_amount(line.debit, decimal_comma=False),
                    _fmt_amount(line.credit, decimal_comma=False),
                ]
            )
    return _csv_bytes(rows, delimiter=",")


def invoices_to_generic_csv(invoices: list[Invoice]) -> bytes:
    rows = [
        [
            "ID",
            "Type",
            "Fournisseur",
            "Date",
            "Numéro",
            "Compte",
            "Libellé",
            "Débit",
            "Crédit",
            "Imputation",
        ]
    ]
    for invoice in invoices:
        entry = _entry(invoice)
        if not entry or not entry.lines:
            continue
        for line in entry.lines:
            rows.append(
                [
                    str(invoice.id),
                    invoice.document_type or "",
                    invoice.supplier or "",
                    invoice.invoice_date or "",
                    invoice.invoice_number or "",
                    line.account,
                    line.label,
                    _fmt_amount(line.debit),
                    _fmt_amount(line.credit),
                    entry.imputation or "",
                ]
            )
    return _csv_bytes(rows)


EXPORTERS = {
    "fec": (invoices_to_fec, "text/plain; charset=utf-8", "fec.txt"),
    "sage": (invoices_to_sage, "text/csv; charset=utf-8", "sage.csv"),
    "pennylane": (invoices_to_pennylane, "text/csv; charset=utf-8", "pennylane.csv"),
    "cegid": (invoices_to_cegid, "text/csv; charset=utf-8", "cegid.csv"),
    "ebp": (invoices_to_ebp, "text/csv; charset=utf-8", "ebp.csv"),
    "odoo": (invoices_to_odoo, "text/csv; charset=utf-8", "odoo.csv"),
    "csv": (invoices_to_generic_csv, "text/csv; charset=utf-8", "ecritures.csv"),
}


def export_software(target: str, invoices: list[Invoice]) -> tuple[bytes, str, str]:
    key = target.lower().strip()
    if key not in EXPORTERS:
        raise ValueError(f"Format inconnu: {target}. Formats: {', '.join(SOFTWARE_TARGETS)}")
    fn, media, filename = EXPORTERS[key]
    return fn(invoices), media, filename
