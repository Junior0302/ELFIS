"""RuleEngine — règles métier locales (hints comptes / direction)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.accounting_engine.enums import DocumentDirection
from app.agents.mapper import IMPUTATION_BY_TYPE


@dataclass
class RuleHints:
    direction: str
    document_type: str
    account_hints: dict[str, str] = field(default_factory=dict)
    applied: list[str] = field(default_factory=list)
    exempt_vat: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "document_type": self.document_type,
            "account_hints": self.account_hints,
            "applied": self.applied,
            "exempt_vat": self.exempt_vat,
        }


class RuleEngine:
    """Réutilise IMPUTATION_BY_TYPE du mapper historique — ne duplique pas le mapping complet."""

    def analyze(self, payload: dict[str, Any]) -> RuleHints:
        doc_type = (payload.get("document_type") or payload.get("schema_document_type") or "invoice").lower()
        direction_in = (payload.get("direction") or "").lower()

        # Direction
        if direction_in in {d.value for d in DocumentDirection}:
            direction = direction_in
        elif doc_type in {"customer_invoice", "sales_invoice", "facture_vente", "quote"}:
            direction = DocumentDirection.SALE.value
        elif doc_type in {"credit_note", "avoir"}:
            direction = DocumentDirection.CREDIT_NOTE.value
        elif doc_type in {"bank_statement", "releve"}:
            direction = DocumentDirection.BANK.value
        elif doc_type in {"receipt", "ticket"}:
            direction = DocumentDirection.CASH.value
        else:
            direction = DocumentDirection.PURCHASE.value

        applied: list[str] = [f"direction:{direction}"]
        hints: dict[str, str] = {}

        # Map FR types for IMPUTATION_BY_TYPE
        fr_key = {
            "invoice": "facture",
            "supplier_invoice": "facture",
            "credit_note": "avoir",
            "receipt": "ticket",
            "expense": "note_frais",
            "bank_statement": "releve",
            "quote": "devis",
        }.get(doc_type, doc_type if doc_type in IMPUTATION_BY_TYPE else "facture")

        if fr_key in IMPUTATION_BY_TYPE:
            acc, label = IMPUTATION_BY_TYPE[fr_key]
            if acc:
                hints["expense_or_revenue"] = acc
                applied.append(f"imputation:{fr_key}->{acc}")
            if fr_key == "devis":
                applied.append("devis_sans_ecriture")

        # Avoir = reverse purchase direction for journal, but accounts like purchase credit note
        if direction == DocumentDirection.CREDIT_NOTE.value:
            direction = DocumentDirection.PURCHASE.value  # journal ACH
            applied.append("avoir_traite_comme_achat_inverse")

        exempt = bool(payload.get("vat_exempt") or payload.get("exempt_vat"))
        if exempt:
            applied.append("tva_exoneree")

        return RuleHints(
            direction=direction,
            document_type=doc_type,
            account_hints=hints,
            applied=applied,
            exempt_vat=exempt,
        )
