"""Validation métier des documents commerciaux (devis / facture / avoir)."""

from __future__ import annotations

from typing import Any


class SalesDocumentValidationError(ValueError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message)
        self.code = code
        self.message = message


def _normalized_lines(lines: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in lines or []:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "").strip()
        if not label:
            continue
        try:
            quantity = float(raw.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0.0
        try:
            unit_price = float(raw.get("unit_price", raw.get("unit_price_ht", 0)))
        except (TypeError, ValueError):
            unit_price = 0.0
        out.append({"label": label, "quantity": quantity, "unit_price": unit_price})
    return out


def validate_sales_document_payload(
    *,
    doc_type: str,
    customer_name: str,
    customer_id: int | None,
    amount_ht: float,
    vat_rate: float,
    lines: list[dict[str, Any]] | None,
) -> None:
    """Refuse les documents commercialement vides (client / lignes / montants incohérents).

    Aligné sur le composer frontend :
    - client obligatoire (nom ou customer_id) ;
    - au moins une ligne avec désignation ;
    - quantité > 0, prix unitaire ≥ 0 ;
    - TVA 0–100 %, HT ≥ 0.

    Un document à 0 € HT reste autorisé si les lignes sont présentes (ex. prestation gratuite).
    """
    if doc_type not in ("devis", "facture", "avoir"):
        raise SalesDocumentValidationError("Type de document invalide.", code="invalid_doc_type")

    if not (customer_name or "").strip() and customer_id is None:
        raise SalesDocumentValidationError(
            "Indiquez le client (nom ou identifiant client).",
            code="customer_required",
        )

    try:
        ht = float(amount_ht)
    except (TypeError, ValueError):
        raise SalesDocumentValidationError("Montant HT invalide.", code="invalid_amount_ht") from None
    if ht < 0:
        raise SalesDocumentValidationError("Le montant HT ne peut pas être négatif.", code="invalid_amount_ht")

    try:
        vat = float(vat_rate)
    except (TypeError, ValueError):
        raise SalesDocumentValidationError("Taux de TVA invalide.", code="invalid_vat_rate") from None
    if vat < 0 or vat > 100:
        raise SalesDocumentValidationError(
            "Indiquez un taux de TVA entre 0 et 100 %.",
            code="invalid_vat_rate",
        )

    normalized = _normalized_lines(lines)
    if not normalized:
        raise SalesDocumentValidationError(
            "Ajoutez au moins une ligne avec une désignation.",
            code="lines_required",
        )

    for line in normalized:
        if line["quantity"] <= 0:
            raise SalesDocumentValidationError(
                f"Quantité invalide pour « {line['label']} » (doit être > 0).",
                code="invalid_line_quantity",
            )
        if line["unit_price"] < 0:
            raise SalesDocumentValidationError(
                f"Prix unitaire invalide pour « {line['label']} » (doit être ≥ 0).",
                code="invalid_line_price",
            )
