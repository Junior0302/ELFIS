from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_saas import Contact
from app.services.contacts.duplicate_service import find_duplicates, suggested_action_from_matches
from app.services.contacts.normalize import normalize_company_name


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _contact(db, org_id=1, **kwargs) -> Contact:
    defaults = dict(
        organization_id=org_id,
        contact_type="supplier",
        status="active",
        company_name="Renault Strasbourg",
        siret="",
        siren="",
        vat_number="",
        email="",
        postal_code="",
        city="",
    )
    defaults.update(kwargs)
    c = Contact(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_normalize_company_name_strips_legal_forms():
    assert normalize_company_name("Renault Strasbourg SAS") == "renault strasbourg"
    assert normalize_company_name("Renault - Strasbourg") == "renault strasbourg"
    assert normalize_company_name("Renault Strasbourg S.A.S.") == "renault strasbourg"


def test_existing_siret_blocks_duplicate_score():
    db = _session()
    _contact(db, siret="12345678900012", company_name="Renault Strasbourg")
    matches = find_duplicates(
        db,
        organization_id=1,
        extracted={"company_name": "Autre", "siret": "123 456 789 00012"},
    )
    assert matches[0]["match_type"] == "siret"
    assert matches[0]["match_score"] == 100
    action, contact_id = suggested_action_from_matches(matches)
    assert action == "link_existing_contact"
    assert contact_id == matches[0]["contact_id"]


def test_existing_vat_returns_contact():
    db = _session()
    c = _contact(db, vat_number="FR93552081317", company_name="Fournisseur TVA")
    matches = find_duplicates(
        db,
        organization_id=1,
        extracted={"company_name": "X", "vat_number": "FR93 552 081 317"},
    )
    assert matches[0]["contact_id"] == c.id
    assert matches[0]["match_type"] == "vat_number"


def test_similar_names_produce_possible_duplicate():
    db = _session()
    _contact(db, company_name="Renault Strasbourg", city="Strasbourg", postal_code="67000")
    matches = find_duplicates(
        db,
        organization_id=1,
        extracted={
            "company_name": "Renault Strasbourg SAS",
            "postal_code": "67000",
            "city": "Strasbourg",
        },
    )
    assert matches
    assert matches[0]["match_score"] >= 75
    action, _ = suggested_action_from_matches(matches)
    assert action in {"link_existing_contact", "review_possible_duplicate"}


def test_workspaces_are_isolated():
    db = _session()
    _contact(db, org_id=1, siret="12345678900012", company_name="Alpha Unique SAS")
    _contact(db, org_id=2, siret="99999999900099", company_name="Beta Different SARL")
    matches = find_duplicates(
        db,
        organization_id=2,
        extracted={"company_name": "Alpha Unique SAS", "siret": "12345678900012"},
    )
    assert matches == []
