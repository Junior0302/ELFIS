"""JournalResolver — choix automatique du journal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.accounting_engine.enums import DocumentDirection, JournalCode
from app.config import settings


@dataclass
class JournalChoice:
    code: str
    label: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "label": self.label, "reason": self.reason}


_LABELS = {
    JournalCode.ACH.value: "Achats",
    JournalCode.VTE.value: "Ventes",
    JournalCode.BQ.value: "Banque",
    JournalCode.CA.value: "Caisse",
    JournalCode.OD.value: "Opérations diverses",
}


class JournalResolver:
    def resolve(
        self,
        *,
        direction: str,
        document_type: str | None = None,
        preferred_journal: str | None = None,
    ) -> JournalChoice:
        if preferred_journal:
            code = preferred_journal.upper()
            return JournalChoice(
                code=code,
                label=_LABELS.get(code, code),
                reason="apprentissage_ou_preference",
            )

        doc = (document_type or "").lower()
        direction = (direction or DocumentDirection.PURCHASE.value).lower()

        if direction == DocumentDirection.SALE.value or doc in {
            "customer_invoice",
            "sales_invoice",
            "facture_vente",
            "quote",
        }:
            code = getattr(settings, "elfis_default_sales_journal", None) or JournalCode.VTE.value
            return JournalChoice(code=code, label=_LABELS.get(code, "Ventes"), reason="direction_vente")

        if direction == DocumentDirection.BANK.value or doc in {
            "bank_statement",
            "releve",
        }:
            return JournalChoice(
                code=JournalCode.BQ.value, label="Banque", reason="document_banque"
            )

        if direction == DocumentDirection.CASH.value or doc in {"receipt", "ticket", "caisse"}:
            return JournalChoice(
                code=JournalCode.CA.value, label="Caisse", reason="document_caisse"
            )

        if direction == DocumentDirection.OD.value:
            return JournalChoice(
                code=JournalCode.OD.value, label="Opérations diverses", reason="od"
            )

        # Achats / avoirs par défaut
        code = getattr(settings, "elfis_default_purchase_journal", None) or JournalCode.ACH.value
        return JournalChoice(
            code=code,
            label=_LABELS.get(code, "Achats"),
            reason="direction_achat",
        )
