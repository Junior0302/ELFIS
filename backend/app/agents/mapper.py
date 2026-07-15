from __future__ import annotations

from app.schemas import AccountingEntry, AccountingLine, ExtractionResult

# Imputation type → compte de charge par défaut (modifiable en paramètres)
IMPUTATION_BY_TYPE: dict[str, tuple[str, str]] = {
    "facture": ("606", "Achats / charges"),
    "avoir": ("606", "Avoir achat"),
    "ticket": ("625", "Notes de frais / tickets"),
    "note_frais": ("625", "Notes de frais"),
    "releve": ("401", "Relevé fournisseur"),
    "devis": ("", "Devis — pas d'écriture à comptabiliser"),
    "autre": ("606", "Charge diverse"),
}


def map_accounting(
    extraction: ExtractionResult,
    *,
    expense_account: str = "606",
    vat_account: str = "44566",
    supplier_account: str = "401",
) -> AccountingEntry:
    supplier = extraction.supplier or "Fournisseur"
    ht = float(extraction.amount_ht or 0)
    tva = float(extraction.amount_tva or 0)
    ttc = float(extraction.amount_ttc or (ht + tva))
    doc = (extraction.document_type or "facture").lower()
    piece_ref = extraction.invoice_number or "SANS-REF"
    piece_date_fec = _to_fec_date(extraction.invoice_date)

    suggested_account, imputation_label = IMPUTATION_BY_TYPE.get(doc, ("606", "Charge"))
    charge_account = expense_account if doc in ("facture", "avoir", "autre") else (suggested_account or expense_account)

    # Devis : aucune écriture générée
    if doc == "devis":
        return AccountingEntry(
            journal="ACH",
            journal_lib="Achats",
            label=f"Devis {piece_ref} — {supplier}",
            piece_ref=piece_ref,
            piece_date=piece_date_fec,
            lines=[],
            explanation="Devis détecté : aucune écriture comptable à générer. En attente de facture.",
            imputation=imputation_label,
        )

    is_credit = doc == "avoir"
    label = f"{doc.replace('_', ' ').title()} {piece_ref} — {supplier}".strip()

    if is_credit:
        lines = [
            AccountingLine(account=supplier_account, label=f"Fournisseur {supplier}", debit=ttc, credit=0),
            AccountingLine(account=charge_account, label=imputation_label, debit=0, credit=ht),
            AccountingLine(account=vat_account, label="TVA déductible", debit=0, credit=tva),
        ]
        explanation = (
            f"Imputation avoir : crédit {charge_account} ({imputation_label}) + {vat_account}, "
            f"débit fournisseur {supplier_account}."
        )
    else:
        lines = [
            AccountingLine(account=charge_account, label=imputation_label, debit=ht, credit=0),
            AccountingLine(account=vat_account, label="TVA déductible", debit=tva, credit=0),
            AccountingLine(account=supplier_account, label=f"Fournisseur {supplier}", debit=0, credit=ttc),
        ]
        explanation = (
            f"Imputation {doc} : débit {charge_account} ({imputation_label}) + {vat_account}, "
            f"crédit fournisseur {supplier_account}."
        )

    return AccountingEntry(
        journal="ACH",
        journal_lib="Achats",
        label=label,
        piece_ref=piece_ref,
        piece_date=piece_date_fec,
        lines=lines,
        explanation=explanation,
        imputation=f"{charge_account} — {imputation_label}",
    )


def _to_fec_date(value: str | None) -> str:
    if not value:
        return ""
    # JJ-MM-AAAA or JJ/MM/AAAA → AAAAMMJJ
    parts = re_split_date(value)
    if parts:
        d, m, y = parts
        return f"{y}{m}{d}"
    return value.replace("-", "").replace("/", "")


def re_split_date(value: str) -> tuple[str, str, str] | None:
    import re

    m = re.match(r"(\d{2})[-/](\d{2})[-/](\d{4})", value.strip())
    if m:
        return m.group(1), m.group(2), m.group(3)
    m2 = re.match(r"(\d{4})[-/](\d{2})[-/](\d{2})", value.strip())
    if m2:
        return m2.group(3), m2.group(2), m2.group(1)
    return None
