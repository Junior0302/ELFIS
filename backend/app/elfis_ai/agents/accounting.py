from __future__ import annotations

from app.elfis_ai.schemas import AccountingBlock, AccountingLineExplain
from app.models import CompanySettings, Invoice
from app.schemas import AccountingEntry


ACCOUNT_JUSTIFICATIONS = {
    "606": (
        "Le compte 606 est proposé car la facture concerne des fournitures et du petit matériel "
        "destiné au fonctionnement courant de l'entreprise."
    ),
    "625": (
        "Le compte 625 est proposé car le document ressemble à une note de frais ou un ticket "
        "lié aux déplacements / réceptions."
    ),
    "44566": "Le compte 44566 enregistre la TVA déductible potentiellement récupérable.",
    "401": "Le compte 401 représente la dette fournisseur correspondant au montant TTC.",
}


def run_accounting_agent(invoice: Invoice, settings: CompanySettings) -> AccountingBlock:
    entry: AccountingEntry | None = None
    if invoice.accounting_entry:
        try:
            entry = AccountingEntry.model_validate_json(invoice.accounting_entry)
        except Exception:
            entry = None

    if not entry:
        return AccountingBlock(
            status="insufficient_data",
            review_required=True,
            explanations=["Écriture comptable indisponible."],
        )

    doc = (invoice.document_type or "facture").lower()
    lines: list[AccountingLineExplain] = []
    total_debit = 0.0
    total_credit = 0.0
    potential_immo = False
    ht = float(invoice.amount_ht or 0)

    for line in entry.lines:
        total_debit += float(line.debit or 0)
        total_credit += float(line.credit or 0)
        account = line.account
        certainty = "certain"
        justification = ACCOUNT_JUSTIFICATIONS.get(
            account,
            f"Le compte {account} est proposé selon les paramètres comptables de l'organisation.",
        )
        if account == settings.expense_account and ht >= 500:
            potential_immo = True
            certainty = "review_required"
            justification += (
                " Le montant peut nécessiter une vérification d'immobilisation (compte 2xx)."
            )
        elif account == settings.expense_account:
            certainty = "probable"
        lines.append(
            AccountingLineExplain(
                account=account,
                label=line.label,
                debit=float(line.debit or 0),
                credit=float(line.credit or 0),
                justification=justification,
                certainty=certainty,  # type: ignore[arg-type]
            )
        )

    balanced = abs(total_debit - total_credit) < 0.02
    review = (
        not balanced
        or potential_immo
        or doc == "devis"
        or invoice.needs_review
        or not lines
    )
    confidence = 0.92 if balanced and not review else 0.65 if balanced else 0.35

    explanations = [entry.explanation] if entry.explanation else []
    if doc == "devis":
        explanations.append("Devis : aucune écriture à enregistrer tant que la facture n'est pas reçue.")
    if potential_immo:
        explanations.append("Immobilisation potentielle : validation humaine nécessaire.")
    if not balanced and lines:
        explanations.append("Écriture déséquilibrée : contrôle requis avant enregistrement.")

    return AccountingBlock(
        journal=entry.journal,
        entry_date=invoice.invoice_date,
        label=entry.label,
        currency="EUR",
        lines=lines,
        total_debit=round(total_debit, 2),
        total_credit=round(total_credit, 2),
        balanced=balanced,
        confidence=confidence,
        review_required=review,
        potential_immobilization=potential_immo,
        explanations=explanations,
        status="review_required" if review else "ok",
    )
