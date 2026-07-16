from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.elfis_ai.history import find_duplicate_candidates
from app.elfis_ai.schemas import AnomalyItem, ChecksBlock, ExtractionBlock
from app.models import Invoice


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.replace("/", "-") if fmt != "%Y-%m-%d" else value, fmt)
        except ValueError:
            continue
    # try normalized
    cleaned = value.replace("/", "-")
    try:
        return datetime.strptime(cleaned, "%d-%m-%Y")
    except ValueError:
        return None


def run_anomaly_agent(
    db: Session,
    invoice: Invoice,
    extraction: ExtractionBlock,
) -> ChecksBlock:
    anomalies: list[AnomalyItem] = []
    calc: list[AnomalyItem] = []
    tax: list[AnomalyItem] = []

    ht = invoice.amount_ht
    tva = invoice.amount_tva
    ttc = invoice.amount_ttc
    rate = invoice.vat_rate

    if ht is not None and tva is not None and ttc is not None:
        expected = round(float(ht) + float(tva), 2)
        if abs(expected - float(ttc)) > 0.05:
            item = AnomalyItem(
                id="calc_ht_tva_ttc",
                category="calcul",
                title="Incohérence HT + TVA = TTC",
                description=f"HT ({ht}) + TVA ({tva}) = {expected}, mais TTC déclaré = {ttc}.",
                severity="elevee",
                field="amount_ttc",
                detected_value=ttc,
                expected_value=expected,
                recommended_action="Corriger les montants avant enregistrement.",
                blocking=True,
            )
            calc.append(item)
            anomalies.append(item)

    if ht is not None and tva is not None and float(ht) > 0 and rate is not None:
        expected_rate = round(float(tva) / float(ht) * 100, 1)
        if abs(expected_rate - float(rate)) > 0.6:
            item = AnomalyItem(
                id="tax_rate_mismatch",
                category="tva",
                title="Taux de TVA incohérent",
                description=f"Taux déclaré {rate} % vs calculé {expected_rate} %.",
                severity="moyenne",
                field="vat_rate",
                detected_value=rate,
                expected_value=expected_rate,
                recommended_action="Vérifier le taux de TVA appliqué.",
                blocking=False,
            )
            tax.append(item)
            anomalies.append(item)

    if rate is not None and float(rate) not in (0, 2.1, 5.5, 10, 20):
        item = AnomalyItem(
            id="tax_rate_unusual",
            category="tva",
            title="Taux de TVA inhabituel",
            description=f"Taux {rate} % hors barème courant FR.",
            severity="faible",
            field="vat_rate",
            detected_value=rate,
            expected_value="0 / 2.1 / 5.5 / 10 / 20",
            recommended_action="Confirmer le taux applicable.",
            blocking=False,
        )
        tax.append(item)
        anomalies.append(item)

    for amount_name, amount in (("amount_ht", ht), ("amount_tva", tva), ("amount_ttc", ttc)):
        if amount is not None and float(amount) < 0 and (invoice.document_type or "") != "avoir":
            item = AnomalyItem(
                id=f"neg_{amount_name}",
                category="montant",
                title="Montant négatif inhabituel",
                description=f"{amount_name} est négatif sur un document non-avoir.",
                severity="moyenne",
                field=amount_name,
                detected_value=amount,
                expected_value=">= 0",
                recommended_action="Vérifier s'il s'agit d'un avoir.",
                blocking=False,
            )
            anomalies.append(item)

    if not invoice.invoice_number:
        anomalies.append(
            AnomalyItem(
                id="missing_number",
                category="completude",
                title="Numéro de document manquant",
                description="Aucun numéro de facture détecté.",
                severity="moyenne",
                field="invoice_number",
                recommended_action="Saisir le numéro du document.",
                blocking=False,
            )
        )

    issue = _parse_date(invoice.invoice_date)
    if invoice.invoice_date and issue is None:
        anomalies.append(
            AnomalyItem(
                id="invalid_date",
                category="date",
                title="Date invalide",
                description=f"Date d'émission non reconnue : {invoice.invoice_date}.",
                severity="moyenne",
                field="invoice_date",
                detected_value=invoice.invoice_date,
                recommended_action="Corriger le format JJ-MM-AAAA.",
                blocking=False,
            )
        )

    due_raw = extraction.document.get("due_date")
    due_val = due_raw.value if due_raw else None
    due = _parse_date(str(due_val) if due_val else None)
    if issue and due and due < issue:
        anomalies.append(
            AnomalyItem(
                id="due_before_issue",
                category="date",
                title="Échéance antérieure à la date",
                description="La date d'échéance est avant la date d'émission.",
                severity="elevee",
                field="due_date",
                detected_value=due_val,
                expected_value=invoice.invoice_date,
                recommended_action="Vérifier les dates du document.",
                blocking=True,
            )
        )

    currency = extraction.document.get("currency")
    if currency and currency.status == "not_available":
        anomalies.append(
            AnomalyItem(
                id="missing_currency",
                category="completude",
                title="Devise absente",
                description="Aucune devise explicitement détectée (EUR assumé par défaut).",
                severity="information",
                field="currency",
                recommended_action="Confirmer la devise du document.",
                blocking=False,
            )
        )

    # Lignes vs totaux
    if extraction.line_items:
        lines_ht = sum(float(i.total_ht or 0) for i in extraction.line_items if i.total_ht is not None)
        if ht is not None and lines_ht > 0 and abs(lines_ht - float(ht)) > 0.5:
            anomalies.append(
                AnomalyItem(
                    id="lines_vs_total",
                    category="calcul",
                    title="Lignes incohérentes avec le total HT",
                    description=f"Somme des lignes HT = {lines_ht:.2f} vs total HT = {ht}.",
                    severity="moyenne",
                    field="line_items",
                    detected_value=lines_ht,
                    expected_value=ht,
                    recommended_action="Contrôler les lignes extraites.",
                    blocking=False,
                )
            )

    duplicates = find_duplicate_candidates(db, organization_id=invoice.organization_id, invoice=invoice)
    if duplicates:
        ids = ", ".join(str(d.id) for d in duplicates[:5])
        anomalies.append(
            AnomalyItem(
                id="duplicate_document",
                category="doublon",
                title="Facture potentiellement dupliquée",
                description=f"Document(s) similaire(s) détecté(s) : #{ids}.",
                severity="elevee",
                field="invoice_number",
                detected_value=invoice.invoice_number,
                expected_value="unique",
                recommended_action="Vérifier qu'il ne s'agit pas d'un doublon avant paiement.",
                blocking=True,
            )
        )

    # Anomalies texte du validator historique
    try:
        legacy = json.loads(invoice.anomalies or "[]")
    except json.JSONDecodeError:
        legacy = []
    for idx, text in enumerate(legacy):
        if not isinstance(text, str):
            continue
        if any(text.lower() in (a.description or "").lower() for a in anomalies):
            continue
        anomalies.append(
            AnomalyItem(
                id=f"legacy_{idx}",
                category="validation",
                title="Contrôle pipeline",
                description=text,
                severity="moyenne",
                recommended_action="Revoir le document.",
                blocking=False,
            )
        )

    missing = json.loads(invoice.missing_fields or "[]") if invoice.missing_fields else []
    for field in missing:
        anomalies.append(
            AnomalyItem(
                id=f"missing_{field}",
                category="completude",
                title=f"Champ essentiel manquant : {field}",
                description=f"Le champ {field} n'a pas été extrait.",
                severity="moyenne",
                field=str(field),
                recommended_action="Compléter manuellement.",
                blocking=False,
            )
        )

    return ChecksBlock(
        calculation_checks=calc,
        tax_checks=tax,
        compliance_checks=[],
        anomalies=anomalies,
    )
