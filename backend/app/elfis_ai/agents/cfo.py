from __future__ import annotations

from app.elfis_ai.schemas import (
    AccountingBlock,
    AnomalyItem,
    CfoSummary,
    FinancialBlock,
    RecommendationItem,
    RiskBlock,
)
from app.models import Invoice


def run_cfo_agent(
    invoice: Invoice,
    anomalies: list[AnomalyItem],
    accounting: AccountingBlock,
    financial: FinancialBlock,
    risk: RiskBlock,
    recommendations: list[RecommendationItem],
) -> CfoSummary:
    doc_type = (invoice.document_type or "document").replace("_", " ")
    amount = f"{float(invoice.amount_ttc):.2f} €" if invoice.amount_ttc is not None else "montant inconnu"
    supplier = invoice.supplier or "fournisseur inconnu"

    what = f"Il s'agit d'un(e) {doc_type} de {amount} concernant {supplier}."

    blocking = [a for a in anomalies if a.blocking]
    if blocking:
        coherent = (
            f"Le document présente {len(blocking)} anomalie(s) bloquante(s) "
            f"et nécessite une vérification avant enregistrement."
        )
    elif anomalies:
        coherent = (
            f"Le document est globalement exploitable, avec {len(anomalies)} point(s) "
            f"à contrôler (aucune anomalie bloquante)."
        )
    else:
        coherent = "Le document semble cohérent : aucun contrôle bloquant n'a été relevé."

    impact_parts = []
    if financial.monthly_weight_pct is not None:
        impact_parts.append(f"elle représente {financial.monthly_weight_pct} % des achats du mois")
    if financial.cash_impact:
        impact_parts.append(financial.cash_impact.lower())
    if accounting.potential_immobilization:
        impact_parts.append("une vérification d'immobilisation peut être nécessaire")
    if not impact_parts:
        impact_parts.append("l'impact financier détaillé est limité faute de données historiques")
    main_impact = "Impact principal : " + " ; ".join(impact_parts) + "."

    next_action = "Relire le document et compléter les champs manquants."
    urgent = next((r for r in recommendations if r.priority in ("urgente", "haute")), None)
    if urgent:
        next_action = urgent.action or urgent.title
    elif invoice.status == "ready":
        next_action = "Enregistrer le document et planifier le paiement si applicable."

    summary = (
        f"Cette {doc_type} fournisseur de {amount} est "
        f"{'globalement cohérente' if not blocking else 'à vérifier'}. "
    )
    if accounting.balanced and not blocking:
        summary += "Les calculs et l'écriture proposée sont exploitables. "
    if financial.recommended_payment_date:
        summary += f"Le paiement est attendu avant le {financial.recommended_payment_date}. "
    if risk.level in ("eleve", "critique"):
        summary += "Un risque potentiel a été signalé — vérification recommandée. "
    summary += next_action

    limitations = []
    if financial.status == "insufficient_data":
        limitations.append("Historique fournisseur insuffisant pour une comparaison fiable.")
    if risk.never_assert_fraud:
        limitations.append("Les signaux de risque ne constituent pas une preuve de fraude.")
    limitations.append("L'analyse fiscale est indicative et non un conseil juridique.")

    return CfoSummary(
        what_is_it=what,
        is_coherent=coherent,
        main_impact=main_impact,
        next_action=next_action,
        summary=summary.strip(),
        limitations=limitations,
    )
