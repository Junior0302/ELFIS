from __future__ import annotations

import json

from app.elfis_ai.schemas import (
    AccountingBlock,
    AnomalyItem,
    ConfidenceBlock,
    ConfidenceFactor,
    ExtractionBlock,
)
from app.models import Invoice


def run_confidence_agent(
    invoice: Invoice,
    extraction: ExtractionBlock,
    accounting: AccountingBlock,
    anomalies: list[AnomalyItem],
) -> ConfidenceBlock:
    factors: list[ConfidenceFactor] = []
    missing: list[str] = []
    uncertain: list[str] = []
    score = float(invoice.confidence_score or 0.5)

    raw_len = 0
    if invoice.raw_extraction:
        try:
            raw_len = len(json.loads(invoice.raw_extraction).get("raw_text") or "")
        except json.JSONDecodeError:
            raw_len = 0

    if raw_len > 120:
        factors.append(ConfidenceFactor(label="Document lisible", positive=True, detail="Texte OCR suffisant."))
        score = min(1.0, score + 0.05)
    else:
        factors.append(ConfidenceFactor(label="Lisibilité limitée", positive=False, detail="Peu de texte exploitable."))
        score = max(0.1, score - 0.1)

    if invoice.invoice_number:
        factors.append(ConfidenceFactor(label="Numéro détecté", positive=True))
    else:
        missing.append("invoice_number")
        factors.append(ConfidenceFactor(label="Numéro manquant", positive=False))

    blocking = [a for a in anomalies if a.blocking]
    calc_ok = not any(a.id == "calc_ht_tva_ttc" for a in anomalies)
    if calc_ok and invoice.amount_ttc is not None:
        factors.append(ConfidenceFactor(label="Montants cohérents", positive=True))
        score = min(1.0, score + 0.05)
    elif not calc_ok:
        factors.append(ConfidenceFactor(label="Incohérence de montants", positive=False))
        score = max(0.1, score - 0.2)

    if any(a.category == "tva" for a in anomalies):
        factors.append(ConfidenceFactor(label="TVA à vérifier", positive=False))
    elif invoice.vat_rate is not None or invoice.amount_tva == 0:
        factors.append(ConfidenceFactor(label="TVA vérifiée", positive=True))

    if accounting.balanced:
        factors.append(ConfidenceFactor(label="Écriture équilibrée", positive=True))
    elif accounting.lines:
        factors.append(ConfidenceFactor(label="Écriture déséquilibrée", positive=False))
        score = max(0.1, score - 0.1)

    for key, block in (("supplier", extraction.supplier), ("document", extraction.document)):
        for name, field in block.items():
            if field.status == "missing" or field.status == "not_available":
                if name in ("name", "number", "issue_date", "total_ttc"):
                    missing.append(f"{key}.{name}")
            elif field.status == "uncertain":
                uncertain.append(f"{key}.{name}")

    if blocking:
        factors.append(
            ConfidenceFactor(
                label=f"{len(blocking)} anomalie(s) bloquante(s)",
                positive=False,
                detail="Validation humaine recommandée.",
            )
        )
        score = max(0.1, score - 0.15)

    score = round(min(1.0, max(0.0, score)), 3)
    summary = (
        f"Confiance {int(score * 100)} % — "
        f"{sum(1 for f in factors if f.positive)} facteur(s) positif(s), "
        f"{sum(1 for f in factors if not f.positive)} point(s) à vérifier."
    )
    return ConfidenceBlock(
        global_score=score,
        factors=factors,
        missing_fields=sorted(set(missing)),
        uncertain_fields=sorted(set(uncertain)),
        summary=summary,
    )
