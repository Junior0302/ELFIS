"""Stage mapping comptable — réutilise map_accounting + ventes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.accounting.accounting_security import assert_account_code, to_decimal
from app.accounting.accounting_types import AccountingDocumentTypes
from app.agents.mapper import map_accounting
from app.config import settings
from app.schemas import AccountingEntry, AccountingLine, ExtractionResult


def run_accounting_mapping(
    extraction: ExtractionResult,
    *,
    document_type: str,
) -> dict[str, Any]:
    """
    Réutilise map_accounting pour les achats / avoirs.
    Mapping ventes (customer_invoice) via comptes configurables.
    """
    used_defaults: list[str] = []

    if document_type == AccountingDocumentTypes.CUSTOMER_INVOICE:
        entry, used_defaults = _map_sales(extraction)
    elif document_type in (
        AccountingDocumentTypes.SUPPLIER_INVOICE,
        AccountingDocumentTypes.CREDIT_NOTE,
    ):
        # Adapter document_type FR pour le mapper historique
        adapted = extraction.model_copy(
            update={
                "document_type": (
                    "avoir"
                    if document_type == AccountingDocumentTypes.CREDIT_NOTE
                    else "facture"
                )
            }
        )
        purchase = settings.elfis_default_purchase_account
        vat = settings.elfis_default_deductible_vat_account
        supplier = settings.elfis_default_supplier_account
        # Normaliser comptes longs (401000 → 401 pour compat mapper si besoin)
        entry = map_accounting(
            adapted,
            expense_account=purchase,
            vat_account=vat,
            supplier_account=supplier,
        )
        # Remplacer journal par config
        entry.journal = settings.elfis_default_purchase_journal
        used_defaults = ["purchase_account", "vat_account", "supplier_account"]
        # Normaliser lignes en Decimal strings pour persistance
    else:
        return {
            "status": "skipped",
            "errors": [f"Type non supporté pour mapping V1: {document_type}"],
            "warnings": [],
            "journal_code": None,
            "lines": [],
            "balanced": False,
            "used_default_accounts": True,
            "explanation": "Mapping non automatisé pour ce type",
        }

    lines_out = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for line in entry.lines:
        debit = to_decimal(line.debit)
        credit = to_decimal(line.credit)
        total_debit += debit
        total_credit += credit
        raw_code = "".join(c for c in str(line.account) if c.isdigit()) or str(line.account)
        try:
            code = assert_account_code(raw_code)
        except Exception:
            code = raw_code[:16]
        lines_out.append(
            {
                "account_code": code,
                "account_label": line.label,
                "debit": float(debit),
                "credit": float(credit),
                "third_party_name": None,
            }
        )

    from app.accounting.accounting_security import balance_tolerance

    diff = abs(total_debit - total_credit)
    balanced = diff <= balance_tolerance()

    status = "ok" if balanced and lines_out else ("unbalanced" if lines_out else "empty")
    return {
        "status": status,
        "errors": [] if balanced else ["Écriture non équilibrée"],
        "warnings": ["Comptes par défaut utilisés"] if used_defaults else [],
        "journal_code": entry.journal,
        "journal_lib": entry.journal_lib,
        "description": entry.label,
        "reference": entry.piece_ref,
        "piece_date": entry.piece_date,
        "explanation": entry.explanation,
        "imputation": entry.imputation,
        "lines": lines_out,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "balanced": balanced,
        "used_default_accounts": bool(used_defaults),
        "used_defaults": used_defaults,
    }


def _map_sales(extraction: ExtractionResult) -> tuple[AccountingEntry, list[str]]:
    customer = extraction.customer_name or extraction.supplier or "Client"
    ht = float(extraction.amount_ht or 0)
    tva = float(extraction.amount_tva or 0)
    ttc = float(extraction.amount_ttc or (ht + tva))
    ref = extraction.invoice_number or "SANS-REF"
    sales = settings.elfis_default_sales_account
    vat = settings.elfis_default_collected_vat_account
    client = settings.elfis_default_customer_account
    journal = settings.elfis_default_sales_journal
    lines = [
        AccountingLine(account=client, label=f"Client {customer}", debit=ttc, credit=0),
        AccountingLine(account=sales, label="Ventes", debit=0, credit=ht),
        AccountingLine(account=vat, label="TVA collectée", debit=0, credit=tva),
    ]
    entry = AccountingEntry(
        journal=journal,
        journal_lib="Ventes",
        label=f"Facture {ref} — {customer}",
        piece_ref=ref,
        piece_date="",
        lines=lines,
        explanation=(
            f"Imputation vente : débit client {client}, crédit {sales} + {vat}."
        ),
        imputation=f"{sales} — Ventes",
    )
    return entry, ["sales_account", "collected_vat_account", "customer_account"]
