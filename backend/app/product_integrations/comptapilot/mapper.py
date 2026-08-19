"""Mapper transport ELFIS → ComptaPilot — aucun mapping comptable."""

from __future__ import annotations

from typing import Any


_TRANSPORT_FIELDS = (
    "invoice_number",
    "quote_number",
    "issue_date",
    "due_date",
    "validity_date",
    "transaction_date",
    "supplier_name",
    "customer_name",
    "issuer_name",
    "merchant_name",
    "currency",
    "subtotal",
    "tax_amount",
    "total_amount",
    "tax_rate",
    "payment_terms",
)


class ElfisToComptaPilotDocumentMapper:
    """Convertit uniquement des champs documentaires de transport.

    Ne produit jamais : compte, journal, débit, crédit, écriture, traitement fiscal.
    """

    def map_transport(self, package: dict[str, Any]) -> dict[str, Any]:
        fields = ((package.get("extraction") or {}).get("fields")) or {}
        transport: dict[str, Any] = {}
        for key in _TRANSPORT_FIELDS:
            if key in fields:
                val = fields[key]
                if isinstance(val, dict):
                    transport[key] = val.get("normalized_value", val.get("value"))
                else:
                    transport[key] = val
        return {
            "schema": "comptapilot_document_import_transport_v1",
            "organization_id": package.get("organization_id"),
            "document": package.get("document"),
            "classification": package.get("classification"),
            "validation": {
                "result_id": (package.get("validation") or {}).get("result_id"),
                "status": (package.get("validation") or {}).get("status"),
                "issue_codes": list((package.get("validation") or {}).get("issue_codes") or [])[:50],
            },
            "provenance": package.get("provenance"),
            "fields": transport,
            # Explicitement absent : accounting_accounts, journal, entries
        }
