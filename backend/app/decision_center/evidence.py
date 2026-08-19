"""Construction de preuves structurées à partir des sources métier."""

from __future__ import annotations

from typing import Any

from app.decision_center.enums import DecisionEvidenceType, DecisionSourceType


def _fmt_amount(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value):.2f} €"
    except (TypeError, ValueError):
        return str(value)


def evidence_for_accounting_proposal(proposal: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    status = getattr(proposal, "status", None) or ""
    items.append(
        {
            "type": DecisionEvidenceType.SOURCE_STATUS,
            "label": "Statut de la proposition",
            "value": str(status),
            "description": "État actuel dans le pipeline comptable.",
        }
    )
    if bool(getattr(proposal, "requires_review", False)):
        items.append(
            {
                "type": DecisionEvidenceType.RULE_RESULT,
                "label": "Revue humaine requise",
                "value": "oui",
                "description": "Les contrôles métier ont demandé une vérification avant validation.",
            }
        )
    reasons = getattr(proposal, "review_reasons", None) or []
    if isinstance(reasons, list):
        for reason in reasons[:5]:
            items.append(
                {
                    "type": DecisionEvidenceType.REVIEW_REASON,
                    "label": "Motif de revue",
                    "value": str(reason)[:200],
                    "description": "Raison enregistrée par le moteur comptable.",
                }
            )
    fin = getattr(proposal, "financial_validation", None)
    if isinstance(fin, dict):
        diff = fin.get("difference") or fin.get("delta") or fin.get("amount_difference")
        if diff is not None:
            items.append(
                {
                    "type": DecisionEvidenceType.FINANCIAL_DIFFERENCE,
                    "label": "Écart détecté",
                    "value": _fmt_amount(diff) or str(diff),
                    "description": "Écart relevé par le contrôle financier.",
                }
            )
        detected = fin.get("detected_ttc") or fin.get("amount_ttc")
        expected = fin.get("expected_ttc") or fin.get("lines_ttc")
        if detected is not None:
            items.append(
                {
                    "type": DecisionEvidenceType.DETECTED_AMOUNT,
                    "label": "Montant détecté",
                    "value": _fmt_amount(detected) or str(detected),
                    "description": "Montant TTC issu de l’analyse ou du document.",
                }
            )
        if expected is not None:
            items.append(
                {
                    "type": DecisionEvidenceType.EXPECTED_AMOUNT,
                    "label": "Montant attendu",
                    "value": _fmt_amount(expected) or str(expected),
                    "description": "Montant recalculé à partir des lignes.",
                }
            )
    if getattr(proposal, "amount_ttc", None) is not None:
        items.append(
            {
                "type": DecisionEvidenceType.DETECTED_AMOUNT,
                "label": "Montant TTC",
                "value": _fmt_amount(proposal.amount_ttc) or "",
                "description": "Montant TTC de la proposition.",
            }
        )
    vault_id = getattr(proposal, "vault_document_id", None)
    if vault_id:
        items.append(
            {
                "type": DecisionEvidenceType.DOCUMENT_REFERENCE,
                "label": "Document source",
                "value": str(vault_id)[:36],
                "description": "Référence Vault du document associé.",
            }
        )
    return items


def evidence_for_document_analysis(analysis: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    status = getattr(analysis, "status", None) or ""
    items.append(
        {
            "type": DecisionEvidenceType.SOURCE_STATUS,
            "label": "Statut de l’analyse",
            "value": str(status),
            "description": "État courant du moteur Document Intelligence / AI.",
        }
    )
    stage = getattr(analysis, "current_stage", None)
    if stage:
        items.append(
            {
                "type": DecisionEvidenceType.FAILED_STEP
                if status == "failed"
                else DecisionEvidenceType.RULE_RESULT,
                "label": "Étape courante",
                "value": str(stage),
                "description": "Dernière étape enregistrée du traitement.",
            }
        )
    if bool(getattr(analysis, "requires_review", False)):
        items.append(
            {
                "type": DecisionEvidenceType.RULE_RESULT,
                "label": "Confirmation humaine",
                "value": "requise",
                "description": "L’analyse demande une vérification avant suite.",
            }
        )
    quality = getattr(analysis, "quality", None)
    if isinstance(quality, dict):
        band = quality.get("band") or quality.get("status") or quality.get("score_band")
        if band:
            items.append(
                {
                    "type": DecisionEvidenceType.QUALITY_ISSUE,
                    "label": "Indicateur qualité",
                    "value": str(band),
                    "description": "Signal qualité issu du moteur d’analyse.",
                }
            )
    vault_id = getattr(analysis, "vault_document_id", None)
    if vault_id:
        items.append(
            {
                "type": DecisionEvidenceType.DOCUMENT_REFERENCE,
                "label": "Document Vault",
                "value": str(vault_id)[:36],
                "description": "Document concerné par l’analyse.",
            }
        )
    conf = getattr(analysis, "confidence", None)
    if conf is not None:
        try:
            items.append(
                {
                    "type": DecisionEvidenceType.RULE_RESULT,
                    "label": "Confiance moteur",
                    "value": f"{float(conf):.0%}",
                    "description": "Score fourni par le moteur d’analyse (non inventé).",
                }
            )
        except (TypeError, ValueError):
            pass
    return items


def build_evidence(*, source_type: str, source: Any | None) -> list[dict[str, Any]]:
    if source is None:
        return [
            {
                "type": DecisionEvidenceType.SOURCE_STATUS,
                "label": "Source",
                "value": "indisponible",
                "description": "La ressource associée n’est plus disponible.",
            }
        ]
    if source_type == DecisionSourceType.ACCOUNTING_PROPOSAL:
        return evidence_for_accounting_proposal(source)
    if source_type == DecisionSourceType.DOCUMENT_ANALYSIS:
        return evidence_for_document_analysis(source)
    return []
