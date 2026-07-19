from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Invoice
from app.models_saas import Contact, ContactSuggestion, Organization
from app.services.contacts.creation_service import create_contact_from_document
from app.services.contacts.enrichment_service import enrich_contact_from_document
from app.services.contacts.errors import DuplicateContactError, UnsafeBankDetailUpdateError


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _doc(db, org_id=1) -> Invoice:
    db.add(Organization(id=org_id, name=f"Org {org_id}"))
    inv = Invoice(
        organization_id=org_id,
        filename="f.pdf",
        stored_path="/tmp/f.pdf",
        status="ready",
        supplier="Renault Strasbourg",
        anomalies="[]",
        missing_fields="[]",
        raw_extraction=json.dumps({"supplier": "Renault Strasbourg"}),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def test_create_contact_from_document_and_link():
    db = _session()
    doc = _doc(db)
    contact = create_contact_from_document(
        db,
        organization_id=1,
        user_id=1,
        document=doc,
        role="supplier",
        contact_type="supplier",
        confirmed_data={
            "company_name": "Renault Strasbourg",
            "siret": "123 456 789 00012",
            "vat_number": "FR93552081317",
            "postal_code": "67000",
            "city": "Strasbourg",
            "country": "France",
        },
        confidence=94,
    )
    db.refresh(doc)
    assert contact.id
    assert contact.siret == "12345678900012"
    assert contact.source == "document_extraction"
    assert contact.source_document_id == doc.id
    assert doc.supplier_contact_id == contact.id


def test_existing_siret_prevents_creation():
    db = _session()
    doc = _doc(db)
    db.add(
        Contact(
            organization_id=1,
            contact_type="supplier",
            company_name="Existant",
            siret="12345678900012",
        )
    )
    db.commit()
    with pytest.raises(DuplicateContactError):
        create_contact_from_document(
            db,
            organization_id=1,
            user_id=1,
            document=doc,
            role="supplier",
            contact_type="supplier",
            confirmed_data={
                "company_name": "Nouveau",
                "siret": "12345678900012",
            },
        )


def test_enrich_after_confirmation():
    db = _session()
    doc = _doc(db)
    contact = Contact(
        organization_id=1,
        contact_type="supplier",
        company_name="Renault Strasbourg",
        siret="12345678900012",
        email="",
        phone="",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    enriched = enrich_contact_from_document(
        db,
        contact=contact,
        document=doc,
        accepted_fields=["email", "phone"],
        field_values={"email": "facturation@example.com", "phone": "+33300000000"},
        organization_id=1,
        user_id=1,
    )
    assert enriched.email == "facturation@example.com"
    assert enriched.phone == "+33300000000"


def test_iban_not_replaced_without_confirm():
    db = _session()
    doc = _doc(db)
    contact = Contact(
        organization_id=1,
        contact_type="supplier",
        company_name="Banque",
        iban="FR7612345678901234567890123",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    with pytest.raises(UnsafeBankDetailUpdateError):
        enrich_contact_from_document(
            db,
            contact=contact,
            document=doc,
            accepted_fields=["iban"],
            field_values={"iban": "FR7699999999999999999999999"},
            organization_id=1,
            user_id=1,
            confirm_iban=False,
        )


def test_ignored_suggestion_does_not_reappear():
    from app.services.contacts.detection_service import (
        generate_suggestions,
        list_pending_suggestions,
        resolve_suggestion,
    )

    db = _session()
    doc = _doc(db)
    doc.raw_extraction = json.dumps(
        {
            "supplier": "Nouveau Fournisseur SA",
            "supplier_siret": "55208131766522",
            "document_type": "facture",
        }
    )
    db.add(doc)
    db.commit()
    suggestions = generate_suggestions(db, invoice=doc, persist=True)
    assert suggestions
    row = db.query(ContactSuggestion).filter(ContactSuggestion.id == suggestions[0]["id"]).one()
    resolve_suggestion(db, suggestion=row, status="ignored", user_id=1)
    # Régénération : le rôle ignoré ne revient pas
    again = generate_suggestions(db, invoice=doc, persist=True)
    pending = list_pending_suggestions(db, document_id=doc.id, organization_id=1)
    assert again == []
    assert pending == []
