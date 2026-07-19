from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import CompanySettings, Invoice
from app.models_saas import Organization
from app.services.contacts.detection_service import (
    _detect_roles,
    generate_suggestions,
    safe_generate_suggestions,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_org(db, *, org_id=1, name="Ma Boite SAS", siret="12345678900012", vat="FR12345678901"):
    org = Organization(
        id=org_id,
        name=name,
        legal_name=name,
        siren=siret[:9],
        vat_number=vat,
    )
    db.add(org)
    db.add(
        CompanySettings(
            organization_id=org_id,
            company_name=name,
            siret=siret,
            vat_number=vat,
        )
    )
    db.commit()


def _invoice(db, **kwargs) -> Invoice:
    defaults = dict(
        organization_id=1,
        filename="f.pdf",
        stored_path="/tmp/f.pdf",
        mime_type="application/pdf",
        supplier="Renault Strasbourg",
        document_type="facture",
        status="ready",
        needs_review=False,
        anomalies="[]",
        missing_fields="[]",
        raw_extraction=json.dumps(
            {
                "supplier": "Renault Strasbourg",
                "supplier_siret": "55208131766522",
                "supplier_vat": "FR93552081317",
                "supplier_address": "10 rue Test 67000 Strasbourg",
                "document_type": "facture",
            }
        ),
    )
    defaults.update(kwargs)
    inv = Invoice(**defaults)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def test_supplier_invoice_detects_supplier():
    assert _detect_roles("facture") == [("supplier", "supplier")]
    db = _session()
    _seed_org(db)
    inv = _invoice(db)
    suggestions = generate_suggestions(db, invoice=inv, persist=True)
    assert len(suggestions) == 1
    assert suggestions[0]["role"] == "supplier"
    assert suggestions[0]["suggested_contact_type"] == "supplier"
    assert suggestions[0]["suggested_action"] == "create_contact"
    assert suggestions[0]["extracted_data"]["company_name"] == "Renault Strasbourg"


def test_customer_invoice_detects_customer():
    assert _detect_roles("facture", "vente") == [("customer", "customer")]
    db = _session()
    _seed_org(db)
    inv = _invoice(
        db,
        document_type="facture",
        supplier="Ma Boite SAS",
        raw_extraction=json.dumps(
            {
                "document_type": "facture",
                "direction": "vente",
                "supplier": "Ma Boite SAS",
                "supplier_siret": "12345678900012",
                "customer_name": "Client Pro SARL",
                "customer_siret": "89999999900011",
                "customer_address": "1 avenue Client 75001 Paris",
            }
        ),
    )
    suggestions = generate_suggestions(db, invoice=inv, persist=True)
    assert len(suggestions) == 1
    assert suggestions[0]["role"] == "customer"
    assert suggestions[0]["suggested_contact_type"] == "customer"
    assert suggestions[0]["extracted_data"]["company_name"] == "Client Pro SARL"


def test_sent_quote_detects_prospect():
    assert _detect_roles("devis", "envoyé") == [("customer", "prospect")]
    db = _session()
    _seed_org(db)
    inv = _invoice(
        db,
        document_type="devis",
        raw_extraction=json.dumps(
            {
                "document_type": "devis",
                "direction": "envoyé",
                "customer_name": "Prospect SA",
                "customer_address": "2 rue Prospect 69000 Lyon",
            }
        ),
    )
    suggestions = generate_suggestions(db, invoice=inv, persist=True)
    assert len(suggestions) == 1
    assert suggestions[0]["suggested_contact_type"] == "prospect"


def test_own_company_never_suggested():
    db = _session()
    _seed_org(db, name="Ma Boite SAS", siret="12345678900012")
    inv = _invoice(
        db,
        supplier="Ma Boite SAS",
        raw_extraction=json.dumps(
            {
                "supplier": "Ma Boite SAS",
                "supplier_siret": "12345678900012",
                "document_type": "facture",
            }
        ),
    )
    suggestions = generate_suggestions(db, invoice=inv, persist=True)
    assert suggestions == []


def test_safe_generate_never_raises():
    db = _session()
    # Invoice sans organisation / extraction incohérente
    inv = Invoice(
        organization_id=999,
        filename="x.pdf",
        stored_path="/tmp/x.pdf",
        status="ready",
        anomalies="[]",
        missing_fields="[]",
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    assert safe_generate_suggestions(db, inv) == []
