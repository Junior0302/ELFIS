"""Mapping Engine — schémas Sprint 4 → objets métier ComptaPilot."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.import_engine.enums import ImportArtifactKind


SCHEMA_TO_KIND: dict[str, str] = {
    "invoice.v1": ImportArtifactKind.INVOICE.value,
    "quote.v1": ImportArtifactKind.QUOTE.value,
    "credit_note.v1": ImportArtifactKind.CREDIT_NOTE.value,
    "receipt.v1": ImportArtifactKind.RECEIPT.value,
    "bank_statement.v1": ImportArtifactKind.BANK_STATEMENT.value,
    "contract.v1": ImportArtifactKind.CONTRACT.value,
    "generic_document.v1": ImportArtifactKind.GENERIC.value,
}

KIND_TO_DOCUMENT_TYPE: dict[str, str] = {
    ImportArtifactKind.INVOICE.value: "invoice",
    ImportArtifactKind.QUOTE.value: "quote",
    ImportArtifactKind.CREDIT_NOTE.value: "credit_note",
    ImportArtifactKind.RECEIPT.value: "receipt",
    ImportArtifactKind.BANK_STATEMENT.value: "bank_statement",
    ImportArtifactKind.CONTRACT.value: "contract",
    ImportArtifactKind.GENERIC.value: "other",
}


def _nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is default:
            return default
    return cur


def _f(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


@dataclass
class MappedBusinessObject:
    kind: str
    document_type: str
    schema_name: str
    payload: dict[str, Any]
    invoice_fields: dict[str, Any] = field(default_factory=dict)
    contact_candidates: dict[str, dict[str, Any]] = field(default_factory=dict)
    bank_payload: dict[str, Any] | None = None
    accounting_entry: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)


class MappingEngine:
    """Transforme validated_data (Sprint 5) en payload métier importable."""

    def map(
        self,
        *,
        schema_name: str | None,
        validated_data: dict[str, Any],
        filename: str = "document",
        stored_path: str = "",
        mime_type: str = "application/octet-stream",
    ) -> MappedBusinessObject:
        schema = (schema_name or "generic_document.v1").strip()
        kind = SCHEMA_TO_KIND.get(schema, ImportArtifactKind.GENERIC.value)
        doc_type = KIND_TO_DOCUMENT_TYPE.get(kind, "other")
        data = dict(validated_data or {})

        supplier = _nested(data, "supplier") or {}
        customer = _nested(data, "customer") or {}
        merchant = _nested(data, "merchant") or {}
        amounts = _nested(data, "amounts") or {}

        number = (
            data.get("document_number")
            or data.get("quote_number")
            or data.get("credit_note_number")
            or data.get("receipt_number")
            or data.get("contract_number")
            or data.get("statement_number")
        )
        date = (
            data.get("document_date")
            or data.get("issue_date")
            or data.get("credit_note_date")
            or data.get("receipt_date")
            or data.get("contract_date")
            or data.get("statement_date")
        )

        supplier_name = (
            (supplier.get("name") if isinstance(supplier, dict) else None)
            or (merchant.get("name") if isinstance(merchant, dict) else None)
            or data.get("supplier_name")
        )

        invoice_fields: dict[str, Any] = {
            "filename": filename[:255],
            "stored_path": (stored_path or f"import:{schema}")[:512],
            "mime_type": (mime_type or "application/octet-stream")[:100],
            "supplier": (str(supplier_name)[:255] if supplier_name else None),
            "invoice_date": str(date)[:32] if date else None,
            "invoice_number": str(number)[:128] if number else None,
            "amount_ht": _f(amounts.get("subtotal_excluding_tax")),
            "amount_tva": _f(amounts.get("total_tax")),
            "amount_ttc": _f(amounts.get("total_including_tax")),
            "vat_rate": _f(amounts.get("vat_rate")),
            "document_type": doc_type,
            "status": "imported",
            "needs_review": False,
            "raw_extraction": json.dumps(data, ensure_ascii=False, default=str)[:50_000],
        }

        warnings: list[str] = []
        if invoice_fields["amount_ttc"] is None and kind != ImportArtifactKind.CONTRACT.value:
            warnings.append("montant_ttc_absent")

        accounting_entry = None
        if invoice_fields["amount_ttc"] is not None:
            accounting_entry = {
                "source": "import_engine",
                "schema_name": schema,
                "lines": [
                    {
                        "account": "401",
                        "label": "Fournisseur",
                        "credit": invoice_fields["amount_ttc"],
                    },
                    {
                        "account": "606",
                        "label": "Charge",
                        "debit": invoice_fields["amount_ht"] or invoice_fields["amount_ttc"],
                    },
                ],
            }
            if invoice_fields["amount_tva"]:
                accounting_entry["lines"].append(
                    {
                        "account": "44566",
                        "label": "TVA",
                        "debit": invoice_fields["amount_tva"],
                    }
                )
            invoice_fields["accounting_entry"] = json.dumps(
                accounting_entry, ensure_ascii=False, default=str
            )

        contacts: dict[str, dict[str, Any]] = {}
        if isinstance(supplier, dict) and (supplier.get("name") or supplier.get("siret")):
            contacts["supplier"] = _party_to_contact(supplier)
        if isinstance(customer, dict) and (customer.get("name") or customer.get("siret")):
            contacts["customer"] = _party_to_contact(customer)
        if isinstance(merchant, dict) and (merchant.get("name") or merchant.get("siret")):
            contacts.setdefault("supplier", _party_to_contact(merchant))

        bank_payload = None
        if kind == ImportArtifactKind.BANK_STATEMENT.value:
            bank_payload = {
                "label": data.get("account_label") or "Compte importé",
                "bank_name": data.get("bank_name") or "",
                "iban": _nested(data, "account", "iban") or data.get("iban") or "",
                "currency": data.get("currency") or "EUR",
                "transactions": list(data.get("transactions") or []),
            }

        return MappedBusinessObject(
            kind=kind,
            document_type=doc_type,
            schema_name=schema,
            payload=data,
            invoice_fields=invoice_fields,
            contact_candidates=contacts,
            bank_payload=bank_payload,
            accounting_entry=accounting_entry,
            warnings=warnings,
        )


def _party_to_contact(party: dict[str, Any]) -> dict[str, Any]:
    address = party.get("address") if isinstance(party.get("address"), dict) else {}
    return {
        "company_name": party.get("name") or party.get("company_name") or "",
        "trade_name": party.get("trade_name") or "",
        "siren": party.get("siren") or "",
        "siret": party.get("siret") or "",
        "vat_number": party.get("vat_number") or "",
        "email": party.get("email") or "",
        "phone": party.get("phone") or "",
        "address_line_1": address.get("line1") or party.get("address_line_1") or "",
        "address_line_2": address.get("line2") or party.get("address_line_2") or "",
        "postal_code": address.get("postal_code") or party.get("postal_code") or "",
        "city": address.get("city") or party.get("city") or "",
        "country": address.get("country") or party.get("country") or "France",
        "iban": party.get("iban") or "",
        "bic": party.get("bic") or "",
    }
