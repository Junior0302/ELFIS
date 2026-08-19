"""Commercial Proposal Engine — conversion bridge (read-only preview).

Prepares everything needed for a human to convert an accepted proposal into a
Customer/Invoice in ComptaPilot, WITHOUT ever creating anything itself. Never
creates a Customer, never creates an Invoice — that stays a deliberate,
explicit, human-triggered action in another bounded context.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models_saas import Customer
from app.sales_crm.models import SalesCompany, SalesPerson
from app.sales_proposals.models import CommercialProposal
from app.services.contacts.normalize import normalize_company_name, normalize_email, normalize_vat


def _customer_dict(customer: Customer) -> dict[str, Any]:
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email or None,
        "phone": customer.phone or None,
        "vat_number": customer.vat_number or None,
        "address": customer.address or None,
    }


def _company_dict(company: SalesCompany) -> dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name,
        "email": company.email,
        "phone": company.phone,
        "siret": company.siret,
        "vat_number": company.vat_number,
    }


def _candidate(
    *, source: str, match_level: str, matched_on: list[str], record: dict[str, Any]
) -> dict[str, Any]:
    return {
        "source": source,
        "match_level": match_level,
        "matched_on": matched_on,
        "match_reasons": list(matched_on),
        "customer_id": record.get("id"),
        "name": record.get("name"),
        "email": record.get("email"),
        "phone": record.get("phone"),
        "can_select": True,
        "record": record,
    }


def prepare_conversion(
    db: Session,
    *,
    organization_id: int,
    proposal: CommercialProposal,
) -> dict[str, Any]:
    company: SalesCompany | None = None
    person: SalesPerson | None = None

    if proposal.sales_company_id:
        company = (
            db.query(SalesCompany)
            .filter(
                SalesCompany.id == proposal.sales_company_id,
                SalesCompany.organization_id == organization_id,
                SalesCompany.deleted_at.is_(None),
            )
            .first()
        )
    if proposal.person_id:
        person = (
            db.query(SalesPerson)
            .filter(
                SalesPerson.id == proposal.person_id,
                SalesPerson.organization_id == organization_id,
                SalesPerson.deleted_at.is_(None),
            )
            .first()
        )

    linked_customer: dict[str, Any] | None = None
    if proposal.linked_customer_id:
        existing_customer = db.get(Customer, proposal.linked_customer_id)
        if existing_customer and existing_customer.organization_id == organization_id:
            linked_customer = _customer_dict(existing_customer)

    company_vat_norm = normalize_vat(company.vat_number) if company and company.vat_number else ""
    company_siret_norm = normalize_vat(company.siret) if company and company.siret else ""
    company_email_norm = normalize_email(company.email) if company and company.email else ""
    company_name_norm = normalize_company_name(company.name) if company and company.name else ""
    person_email_norm = normalize_email(person.email) if person and person.email else ""

    exact_match: list[dict[str, Any]] = []
    possible_match: list[dict[str, Any]] = []

    if company or person:
        customers = db.query(Customer).filter(Customer.organization_id == organization_id).all()
        for customer in customers:
            cust_vat_norm = normalize_vat(customer.vat_number) if customer.vat_number else ""
            cust_email_norm = normalize_email(customer.email) if customer.email else ""
            cust_name_norm = normalize_company_name(customer.name) if customer.name else ""

            matched_on: list[str] = []
            if company_vat_norm and cust_vat_norm and company_vat_norm == cust_vat_norm:
                matched_on.append("vat_number")
            if company_email_norm and cust_email_norm and company_email_norm == cust_email_norm:
                matched_on.append("email")
            if person_email_norm and cust_email_norm and person_email_norm == cust_email_norm:
                matched_on.append("contact_email")

            if matched_on:
                exact_match.append(
                    _candidate(
                        source="customer",
                        match_level="exact_match",
                        matched_on=matched_on,
                        record=_customer_dict(customer),
                    )
                )
                continue

            if company_name_norm and cust_name_norm and company_name_norm == cust_name_norm:
                possible_match.append(
                    _candidate(
                        source="customer",
                        match_level="possible_match",
                        matched_on=["name"],
                        record=_customer_dict(customer),
                    )
                )

    # Duplicate detection against the SalesCompany registry itself (siret/vat/email/phone/name) —
    # helps surface if this CRM company was already entered twice before converting.
    if company:
        other_companies = (
            db.query(SalesCompany)
            .filter(
                SalesCompany.organization_id == organization_id,
                SalesCompany.id != company.id,
                SalesCompany.deleted_at.is_(None),
            )
            .all()
        )
        for other in other_companies:
            other_vat_norm = normalize_vat(other.vat_number) if other.vat_number else ""
            other_siret_norm = normalize_vat(other.siret) if other.siret else ""
            other_email_norm = normalize_email(other.email) if other.email else ""
            other_phone = (other.phone or "").strip()
            other_name_norm = normalize_company_name(other.name) if other.name else ""

            matched_on = []
            if company_siret_norm and other_siret_norm and company_siret_norm == other_siret_norm:
                matched_on.append("siret")
            if company_vat_norm and other_vat_norm and company_vat_norm == other_vat_norm:
                matched_on.append("vat_number")
            if company_email_norm and other_email_norm and company_email_norm == other_email_norm:
                matched_on.append("email")
            if company and (company.phone or "").strip() and other_phone and (company.phone or "").strip() == other_phone:
                matched_on.append("phone")

            if matched_on:
                exact_match.append(
                    _candidate(
                        source="sales_company",
                        match_level="exact_match",
                        matched_on=matched_on,
                        record=_company_dict(other),
                    )
                )
            elif company_name_norm and other_name_norm and company_name_norm == other_name_norm:
                possible_match.append(
                    _candidate(
                        source="sales_company",
                        match_level="possible_match",
                        matched_on=["name"],
                        record=_company_dict(other),
                    )
                )

    duplicate_candidates = {
        "exact_match": exact_match,
        "possible_match": possible_match,
        "no_match": not exact_match and not possible_match,
    }

    missing_information: list[str] = []
    if not company:
        missing_information.append("Aucune entreprise associée à la proposition")
    else:
        if not (company.vat_number or company.siret):
            missing_information.append("SIRET/TVA de l'entreprise manquants")
        if not company.email and not (person and person.email):
            missing_information.append("Aucune adresse e-mail (entreprise ou contact)")
        if not (company.address_line and company.city):
            missing_information.append("Adresse de facturation incomplète")
    if not person:
        missing_information.append("Aucun contact principal associé")
    if proposal.status != "accepted":
        missing_information.append("La proposition n'est pas encore au statut 'acceptée'")

    preview_name = (company.name if company else None) or (
        f"{person.first_name} {person.last_name}".strip() if person else None
    )
    preview_email = (company.email if company and company.email else None) or (
        person.email if person and person.email else None
    )
    preview_phone = (company.phone if company and company.phone else None) or (
        person.phone if person and person.phone else None
    )
    address_parts = [p for p in [company.address_line if company else None, company.postal_code if company else None, company.city if company else None] if p]

    conversion_preview = {
        "customer_draft": {
            "name": preview_name,
            "email": preview_email,
            "phone": preview_phone,
            "vat_number": (company.vat_number if company else None) or (company.siret if company else None),
            "address": ", ".join(address_parts) if address_parts else None,
        },
        "proposal_number": proposal.proposal_number,
        "currency": proposal.currency,
        "linked_invoice_id": proposal.linked_invoice_id,
    }

    can_link_existing = bool(exact_match or possible_match)
    can_convert = proposal.status == "accepted" and not missing_information

    available_actions = [
        {
            "id": "link_existing_customer",
            "label": "Lier à un client existant",
            "kind": "action",
            "enabled": can_link_existing,
            "reason": None if can_link_existing else "Aucun doublon détecté",
        },
        {
            "id": "review_duplicates",
            "label": "Examiner les doublons potentiels",
            "kind": "action",
            "enabled": bool(exact_match or possible_match),
            "reason": None,
        },
        {
            "id": "create_customer_manually",
            "label": "Créer un nouveau client (action manuelle, hors moteur)",
            "kind": "link",
            "enabled": can_convert,
            "reason": None if can_convert else "Compléter les informations manquantes avant conversion",
        },
    ]

    return {
        "linked_customer": linked_customer,
        "duplicate_candidates": duplicate_candidates,
        "missing_information": missing_information,
        "conversion_preview": conversion_preview,
        "available_actions": available_actions,
    }
