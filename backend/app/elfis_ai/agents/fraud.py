from __future__ import annotations

from app.elfis_ai.history import SupplierHistory
from app.elfis_ai.schemas import AnomalyItem, ExtractionBlock, RiskBlock, RiskFactor
from app.models import Invoice


def run_fraud_agent(
    invoice: Invoice,
    extraction: ExtractionBlock,
    history: SupplierHistory,
    anomalies: list[AnomalyItem],
) -> RiskBlock:
    factors: list[RiskFactor] = []
    score = 0.0

    iban_field = extraction.supplier.get("iban")
    current_iban = (str(iban_field.value).upper() if iban_field and iban_field.value else "") or ""

    if history.document_count == 0:
        factors.append(
            RiskFactor(
                code="new_supplier",
                label="Nouveau fournisseur",
                detail="Aucun historique pour ce fournisseur dans l'organisation.",
            )
        )
        score += 18
    else:
        if current_iban and history.ibans and current_iban not in history.ibans:
            factors.append(
                RiskFactor(
                    code="iban_change",
                    label="Changement d'IBAN",
                    detail="L'IBAN détecté diffère de l'historique connu — vérification recommandée.",
                )
            )
            score += 35

        if invoice.invoice_number and history.invoice_numbers:
            # numéro déjà vu = doublon déjà couvert ; incohérence séquence simple
            pass

        if history.average_amount and invoice.amount_ttc is not None:
            avg = history.average_amount
            if avg > 0 and float(invoice.amount_ttc) > avg * 1.5:
                factors.append(
                    RiskFactor(
                        code="exceptional_amount",
                        label="Montant exceptionnel",
                        detail=(
                            f"Montant {invoice.amount_ttc:.2f} € supérieur de plus de 50 % "
                            f"à la moyenne fournisseur ({avg:.2f} €)."
                        ),
                    )
                )
                score += 22

    if any(a.id == "duplicate_document" for a in anomalies):
        factors.append(
            RiskFactor(
                code="duplicate",
                label="Doublon potentiel",
                detail="Un document similaire existe déjà — risque de double paiement.",
            )
        )
        score += 30

    bic = extraction.supplier.get("bic")
    if current_iban and bic and bic.status == "not_available":
        factors.append(
            RiskFactor(
                code="iban_without_bic",
                label="IBAN sans BIC",
                detail="Coordonnées bancaires incomplètes — vérification recommandée.",
            )
        )
        score += 8

    score = min(100.0, score)
    if score >= 70:
        level = "critique"
    elif score >= 45:
        level = "eleve"
    elif score >= 20:
        level = "modere"
    else:
        level = "faible"

    if not factors:
        explanation = "Aucune anomalie significative détectée sur les signaux de risque disponibles."
        recommendation = "Aucune action urgente liée au risque de fraude."
    else:
        explanation = (
            "Des signaux de risque potentiel ont été détectés. "
            "Cela ne constitue pas une preuve de fraude."
        )
        recommendation = "Vérification recommandée avant paiement, notamment des coordonnées bancaires."

    return RiskBlock(
        score=round(score, 1),
        level=level,  # type: ignore[arg-type]
        factors=factors,
        explanation=explanation,
        recommendation=recommendation,
        never_assert_fraud=True,
    )
