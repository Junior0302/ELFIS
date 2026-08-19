"""Unit tests — Shared Relations adapters & duplicates (no DB merge)."""

from datetime import datetime

from app.models_saas import Contact, Customer
from app.services.shared_relations.adapters import (
    contact_to_shared_relation,
    customer_to_shared_relation,
)
from app.services.shared_relations.contract import make_relation_id, parse_relation_id
from app.services.shared_relations.duplicates import find_duplicates, score_pair


def test_make_and_parse_relation_id():
    rid = make_relation_id("customer", 42)
    assert rid == "customer:42"
    assert parse_relation_id(rid) == ("customer", 42)


def test_customer_adapter():
    row = Customer(
        id=7,
        organization_id=1,
        name="Dupont SAS",
        email="a@dupont.fr",
        phone="0102030405",
        address="1 rue A",
        vat_number="FR123",
        created_at=datetime.utcnow(),
    )
    rel = customer_to_shared_relation(row)
    assert rel.id == "customer:7"
    assert rel.source_system == "customer"
    assert rel.source_entity_id == 7
    assert "customer" in rel.roles
    assert rel.emails == ["a@dupont.fr"]
    assert rel.display_name == "Dupont SAS"


def test_supplier_contact_adapter():
    row = Contact(
        id=9,
        organization_id=1,
        contact_type="supplier",
        status="active",
        company_name="Fourniture SA",
        email="ops@fourniture.fr",
        siren="123456789",
        siret="12345678900012",
    )
    rel = contact_to_shared_relation(row)
    assert rel.id == "contact:9"
    assert "supplier" in rel.roles
    assert rel.siren == "123456789"


def test_duplicate_email_detection():
    a = customer_to_shared_relation(
        Customer(id=1, organization_id=1, name="A", email="same@x.fr", phone="", address="", vat_number="")
    )
    b = contact_to_shared_relation(
        Contact(
            id=2,
            organization_id=1,
            contact_type="supplier",
            company_name="B",
            email="same@x.fr",
        )
    )
    pair = score_pair(a, b)
    assert pair is not None
    assert pair.possible_duplicate is True
    assert "email" in pair.matching_fields
    dups = find_duplicates([a, b])
    assert len(dups) == 1
    # Contrat : détection seulement — pas de champ de fusion auto
    assert not hasattr(pair, "merged_id")


def test_no_duplicate_across_orgs():
    a = customer_to_shared_relation(
        Customer(id=1, organization_id=1, name="A", email="same@x.fr", phone="", address="", vat_number="")
    )
    b = customer_to_shared_relation(
        Customer(id=2, organization_id=2, name="A", email="same@x.fr", phone="", address="", vat_number="")
    )
    assert score_pair(a, b) is None
