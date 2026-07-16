from __future__ import annotations

from app.elfis_ai.schemas import AccountingBlock, ExtractionBlock, TaxBlock
from app.models import Invoice


def run_tax_agent(
    invoice: Invoice,
    extraction: ExtractionBlock,
    accounting: AccountingBlock,
) -> TaxBlock:
    messages: list[str] = []
    tva = invoice.amount_tva
    rate = invoice.vat_rate
    exemption = False
    reverse = False

    vat_ex = extraction.legal_mentions.get("vat_exemption")
    if vat_ex and vat_ex.value:
        exemption = True
        messages.append("Mention d'exonération de TVA détectée.")

    rev = extraction.legal_mentions.get("reverse_charge")
    if rev and rev.value:
        reverse = True
        messages.append("Mention d'autoliquidation détectée.")

    if tva is not None and float(tva) == 0 and not exemption and not reverse:
        messages.append("TVA à 0 sans mention d'exonération explicite — à vérifier.")

    if rate is not None:
        messages.append(f"Taux de TVA utilisé : {rate} %.")

    recoverable = float(tva) if tva is not None and not reverse else (0.0 if reverse else None)
    if recoverable is not None and not reverse:
        messages.append(f"TVA potentiellement déductible : {recoverable:.2f} €.")

    potential_immo = accounting.potential_immobilization
    if potential_immo:
        messages.append(
            "Cette dépense pourrait nécessiter une immobilisation plutôt qu'une charge courante."
        )

    deductible = "indicative"
    if (invoice.document_type or "").lower() in ("facture", "ticket", "note_frais"):
        deductible = "potentiellement_deductible"
    elif (invoice.document_type or "").lower() == "devis":
        deductible = "non_applicable"
        messages.append("Devis : aucune déductibilité tant que la facture n'est pas émise.")

    if not messages:
        messages.append("Données fiscales insuffisantes pour une analyse détaillée.")

    return TaxBlock(
        recoverable_vat=recoverable,
        vat_rate=float(rate) if rate is not None else None,
        exemption=exemption if vat_ex and vat_ex.status != "not_available" else None,
        reverse_charge=reverse if rev and rev.status != "not_available" else None,
        deductible_expense=deductible,
        potential_immobilization=potential_immo,
        messages=messages,
    )
