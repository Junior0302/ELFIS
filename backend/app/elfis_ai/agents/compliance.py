from __future__ import annotations

from app.elfis_ai.schemas import ComplianceBlock, ComplianceItem, ExtractionBlock
from app.models import Invoice


def _status(field) -> str:
    if field is None:
        return "manquant"
    if field.status == "not_available" or field.value in (None, ""):
        return "manquant"
    if field.status == "uncertain":
        return "incertain"
    return "conforme"


def run_compliance_agent(invoice: Invoice, extraction: ExtractionBlock) -> ComplianceBlock:
    items = [
        ComplianceItem(code="supplier_name", label="Identité du fournisseur", status=_status(extraction.supplier.get("name"))),  # type: ignore[arg-type]
        ComplianceItem(code="supplier_address", label="Adresse fournisseur", status=_status(extraction.supplier.get("address"))),  # type: ignore[arg-type]
        ComplianceItem(code="supplier_siret", label="SIRET fournisseur", status=_status(extraction.supplier.get("siret"))),  # type: ignore[arg-type]
        ComplianceItem(code="supplier_vat", label="TVA fournisseur", status=_status(extraction.supplier.get("vat_number"))),  # type: ignore[arg-type]
        ComplianceItem(code="customer_name", label="Identité du client", status=_status(extraction.customer.get("name"))),  # type: ignore[arg-type]
        ComplianceItem(code="invoice_number", label="Numéro de facture", status=_status(extraction.document.get("number"))),  # type: ignore[arg-type]
        ComplianceItem(code="issue_date", label="Date d'émission", status=_status(extraction.document.get("issue_date"))),  # type: ignore[arg-type]
        ComplianceItem(
            code="line_items",
            label="Détail des prestations",
            status="conforme" if extraction.line_items else "manquant",
        ),
        ComplianceItem(code="amounts", label="Montants", status="conforme" if invoice.amount_ttc is not None else "manquant"),
        ComplianceItem(code="currency", label="Devise", status=_status(extraction.document.get("currency"))),  # type: ignore[arg-type]
        ComplianceItem(code="payment_terms", label="Conditions de paiement", status=_status(extraction.document.get("payment_terms"))),  # type: ignore[arg-type]
        ComplianceItem(code="late_penalties", label="Pénalités de retard", status=_status(extraction.legal_mentions.get("late_penalties"))),  # type: ignore[arg-type]
        ComplianceItem(code="recovery_indemnity", label="Indemnité de recouvrement", status=_status(extraction.legal_mentions.get("recovery_indemnity"))),  # type: ignore[arg-type]
        ComplianceItem(code="due_date", label="Échéance", status=_status(extraction.document.get("due_date"))),  # type: ignore[arg-type]
    ]

    ok = sum(1 for i in items if i.status == "conforme")
    missing = sum(1 for i in items if i.status == "manquant")
    ratio = ok / len(items) if items else 0
    if ratio >= 0.75 and missing <= 3:
        synthesis = "elevee"
        summary = "Conformité élevée — quelques mentions peuvent manquer."
    elif ratio >= 0.45:
        synthesis = "partielle"
        summary = "Conformité partielle — vérification nécessaire sur les champs manquants."
    else:
        synthesis = "verification_necessaire"
        summary = "Vérification nécessaire — trop d'éléments essentiels absents ou incertains."

    return ComplianceBlock(items=items, synthesis=synthesis, summary=summary)  # type: ignore[arg-type]
