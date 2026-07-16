from __future__ import annotations

from app.elfis_ai.schemas import (
    AccountingBlock,
    AnomalyItem,
    ComplianceBlock,
    FinancialBlock,
    RecommendationItem,
    RiskBlock,
    TaxBlock,
)
from app.models import Invoice


def run_recommendation_agent(
    invoice: Invoice,
    anomalies: list[AnomalyItem],
    accounting: AccountingBlock,
    financial: FinancialBlock,
    risk: RiskBlock,
    tax: TaxBlock,
    compliance: ComplianceBlock,
) -> list[RecommendationItem]:
    recs: list[RecommendationItem] = []

    for anomaly in anomalies:
        if anomaly.blocking or anomaly.severity in ("elevee", "critique"):
            recs.append(
                RecommendationItem(
                    category="conformite" if anomaly.category == "completude" else "securite",
                    priority="urgente" if anomaly.blocking else "haute",
                    title=anomaly.title,
                    description=anomaly.description,
                    action=anomaly.recommended_action,
                    reason=anomaly.id,
                )
            )

    if risk.factors:
        recs.append(
            RecommendationItem(
                category="securite",
                priority="haute" if risk.level in ("eleve", "critique") else "moyenne",
                title="Vérifier les signaux de risque",
                description=risk.explanation,
                action=risk.recommendation,
                reason="risk_analysis",
            )
        )

    if accounting.review_required:
        recs.append(
            RecommendationItem(
                category="comptabilite",
                priority="haute",
                title="Confirmer le compte comptable proposé",
                description="L'écriture nécessite une validation humaine.",
                action="Revoir l'imputation avant enregistrement.",
                reason="accounting.review_required",
            )
        )

    if accounting.potential_immobilization:
        recs.append(
            RecommendationItem(
                category="comptabilite",
                priority="moyenne",
                title="Immobilisation potentielle",
                description="Cette dépense pourrait nécessiter une immobilisation.",
                action="Valider avec votre plan comptable / expert-comptable.",
                reason="immobilization",
            )
        )

    if financial.recommended_payment_date:
        recs.append(
            RecommendationItem(
                category="paiement",
                priority="moyenne",
                title=f"Régler avant le {financial.recommended_payment_date}",
                description=financial.cash_impact or "Échéance à anticiper.",
                action="Planifier le paiement.",
                reason="due_date",
            )
        )

    if compliance.synthesis == "verification_necessaire":
        recs.append(
            RecommendationItem(
                category="conformite",
                priority="haute",
                title="Compléter les mentions manquantes",
                description=compliance.summary,
                action="Ajouter SIRET / mentions légales si disponibles.",
                reason="compliance",
            )
        )

    if tax.potential_immobilization:
        recs.append(
            RecommendationItem(
                category="fiscalite",
                priority="moyenne",
                title="Contrôle fiscal indicatif",
                description=tax.disclaimer,
                action="Faire valider la déductibilité / immobilisation.",
                reason="tax",
            )
        )

    if invoice.status == "ready" and not any(r.priority in ("haute", "urgente") for r in recs):
        recs.append(
            RecommendationItem(
                category="archivage",
                priority="basse",
                title="Aucune action urgente nécessaire",
                description="Le document peut être enregistré et archivé.",
                action="Enregistrer le document.",
                reason="ready",
            )
        )

    # dédoublonner par titre
    seen: set[str] = set()
    unique: list[RecommendationItem] = []
    for r in recs:
        if r.title in seen:
            continue
        seen.add(r.title)
        unique.append(r)
    return unique[:12]
