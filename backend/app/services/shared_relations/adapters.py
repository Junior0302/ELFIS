"""Adapters: existing ORM rows → SharedRelation (no table mutation)."""

from __future__ import annotations

from app.models_saas import Contact, Customer
from app.services.shared_relations.contract import (
    SharedAddress,
    SharedRelation,
    make_relation_id,
)

try:
    from app.sales_crm.models import SalesCompany
except Exception:  # pragma: no cover
    SalesCompany = None  # type: ignore


def _emails(*values: str | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        e = (v or "").strip()
        if not e:
            continue
        key = e.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _phones(*values: str | None) -> list[str]:
    return _emails(*values)  # same dedupe logic


def customer_to_shared_relation(row: Customer) -> SharedRelation:
    return SharedRelation(
        id=make_relation_id("customer", row.id),
        organization_id=int(row.organization_id),
        party_type="organization",
        display_name=(row.name or "").strip() or f"Client #{row.id}",
        legal_name=(row.name or "").strip(),
        emails=_emails(row.email),
        phones=_phones(row.phone),
        addresses=[
            SharedAddress(line1=(row.address or "").strip())
        ]
        if (row.address or "").strip()
        else [],
        tax_number=(row.vat_number or "").strip(),
        roles=["customer"],
        status="active",
        source_system="customer",
        source_entity_id=int(row.id),
        created_at=getattr(row, "created_at", None),
        updated_at=None,
        links={
            "comptapilot": f"/clients",
            "elfis": f"/platform/relations/{make_relation_id('customer', row.id)}",
        },
    )


def contact_to_shared_relation(row: Contact) -> SharedRelation:
    company = (row.company_name or "").strip()
    trade = (row.trade_name or "").strip()
    person = " ".join(x for x in [(row.first_name or "").strip(), (row.last_name or "").strip()] if x)
    display = company or trade or person or (row.email or "").strip() or f"Contact #{row.id}"
    ctype = (row.contact_type or "customer").strip().lower()
    roles: list = []
    if ctype in ("customer", "customer_and_supplier"):
        roles.append("customer")
    if ctype in ("supplier", "customer_and_supplier"):
        roles.append("supplier")
    if ctype == "prospect":
        roles.append("prospect")
    if not roles:
        roles.append("customer")

    party_type = "organization" if company or trade else ("person" if person else "unknown")
    address = SharedAddress(
        line1=(row.address_line_1 or "").strip(),
        line2=(row.address_line_2 or "").strip(),
        postal_code=(row.postal_code or "").strip(),
        city=(row.city or "").strip(),
        country=(row.country or "").strip(),
    )
    has_address = any(
        [address.line1, address.line2, address.postal_code, address.city, address.country]
    )
    status_raw = (row.status or "active").strip().lower()
    status = status_raw if status_raw in ("active", "inactive", "archived") else "unknown"

    link_path = "/fournisseurs" if "supplier" in roles else "/clients"
    return SharedRelation(
        id=make_relation_id("contact", row.id),
        organization_id=int(row.organization_id),
        party_type=party_type,  # type: ignore[arg-type]
        display_name=display,
        legal_name=company or trade or person,
        first_name=(row.first_name or "").strip(),
        last_name=(row.last_name or "").strip(),
        emails=_emails(row.email),
        phones=_phones(row.phone),
        addresses=[address] if has_address else [],
        tax_number=(row.vat_number or "").strip(),
        siren=(row.siren or "").strip(),
        siret=(row.siret or "").strip(),
        roles=roles,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        source_system="contact",
        source_entity_id=int(row.id),
        created_at=getattr(row, "created_at", None),
        updated_at=getattr(row, "updated_at", None),
        links={
            "comptapilot": link_path,
            "elfis": f"/platform/relations/{make_relation_id('contact', row.id)}",
        },
    )


def sales_company_to_shared_relation(row: "SalesCompany") -> SharedRelation:
    name = (row.name or "").strip() or f"Compte #{row.id}"
    trade = (row.trade_name or "").strip()
    address = SharedAddress(
        line1=(row.address_line or "").strip(),
        postal_code=(row.postal_code or "").strip(),
        city=(row.city or "").strip(),
        country=(row.country or "").strip(),
    )
    has_address = any([address.line1, address.postal_code, address.city, address.country])
    status_raw = (row.status or "active").strip().lower()
    status = status_raw if status_raw in ("active", "inactive", "archived") else "unknown"
    return SharedRelation(
        id=make_relation_id("sales_company", row.id),
        organization_id=int(row.organization_id),
        party_type="organization",
        display_name=trade or name,
        legal_name=name,
        emails=_emails(row.email),
        phones=_phones(row.phone),
        addresses=[address] if has_address else [],
        tax_number=(row.vat_number or "").strip(),
        siret=(row.siret or "").strip(),
        roles=["commercial_account"],
        status=status,  # type: ignore[arg-type]
        source_system="sales_company",
        source_entity_id=int(row.id),
        created_at=getattr(row, "created_at", None),
        updated_at=getattr(row, "updated_at", None),
        links={
            "salespilot": f"/sales/companies",
            "elfis": f"/platform/relations/{make_relation_id('sales_company', row.id)}",
        },
    )
