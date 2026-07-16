from __future__ import annotations

from app.elfis_ai.history import SupplierHistory
from app.elfis_ai.schemas import INSUFFICIENT_DATA, SupplierBlock
from app.models import Invoice


def run_supplier_agent(invoice: Invoice, history: SupplierHistory) -> SupplierBlock:
    if history.document_count == 0:
        return SupplierBlock(
            status=INSUFFICIENT_DATA,
            known_supplier=False,
            document_count=0,
            messages=[
                "Fournisseur nouveau ou sans historique enregistré.",
                "Analyse comparative indisponible : historique insuffisant.",
            ],
        )

    frequency = "insuffisant"
    if history.document_count >= 6:
        frequency = "reguliere"
    elif history.document_count >= 2:
        frequency = "occasionnelle"

    trend = None
    if len(history.amounts) >= 3:
        recent = sum(history.amounts[:2]) / 2
        older = sum(history.amounts[2:5]) / max(1, len(history.amounts[2:5]))
        if older > 0:
            delta = (recent - older) / older * 100
            if delta > 10:
                trend = f"hausse approximative de {delta:.0f} %"
            elif delta < -10:
                trend = f"baisse approximative de {abs(delta):.0f} %"
            else:
                trend = "stable"
    else:
        trend = "insufficient_data"

    messages = [
        f"Fournisseur connu : {history.document_count} document(s) enregistré(s).",
    ]
    if history.average_amount is not None:
        messages.append(f"Montant moyen : {history.average_amount:.2f} €.")
    if history.cumulative_amount is not None:
        messages.append(f"Cumul : {history.cumulative_amount:.2f} €.")
    if history.last_date:
        messages.append(f"Dernier document : {history.last_date}.")

    return SupplierBlock(
        status="ok",
        known_supplier=True,
        document_count=history.document_count,
        last_document_date=history.last_date,
        average_amount=history.average_amount,
        cumulative_amount=history.cumulative_amount,
        purchase_frequency=frequency,
        price_trend=trend,
        iban_history=list(history.ibans),
        previous_anomalies=history.anomaly_count,
        messages=messages,
    )
