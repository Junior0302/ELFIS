from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Invoice
from app.models_saas import Contact, Organization
from app.services.contacts.errors import ContactWorkspaceMismatchError
from app.services.contacts.linking_service import link_document_to_contact


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_link_document_to_contact_same_org():
    db = _session()
    db.add(Organization(id=1, name="Org1"))
    db.commit()
    contact = Contact(
        organization_id=1,
        contact_type="supplier",
        company_name="Fournisseur",
    )
    doc = Invoice(
        organization_id=1,
        filename="f.pdf",
        stored_path="/tmp/f.pdf",
        status="ready",
        anomalies="[]",
        missing_fields="[]",
        raw_extraction="{}",
    )
    db.add_all([contact, doc])
    db.commit()
    db.refresh(contact)
    db.refresh(doc)
    linked = link_document_to_contact(
        db,
        document=doc,
        contact=contact,
        role="supplier",
        organization_id=1,
        user_id=1,
    )
    assert linked.supplier_contact_id == contact.id


def test_cannot_link_contact_from_other_workspace():
    db = _session()
    db.add_all([Organization(id=1, name="A"), Organization(id=2, name="B")])
    contact = Contact(organization_id=2, contact_type="supplier", company_name="Autre")
    doc = Invoice(
        organization_id=1,
        filename="f.pdf",
        stored_path="/tmp/f.pdf",
        status="ready",
        anomalies="[]",
        missing_fields="[]",
    )
    db.add_all([contact, doc])
    db.commit()
    db.refresh(contact)
    db.refresh(doc)
    with pytest.raises(ContactWorkspaceMismatchError):
        link_document_to_contact(
            db,
            document=doc,
            contact=contact,
            role="supplier",
            organization_id=1,
            user_id=1,
        )


def test_suggestion_error_does_not_block_pipeline():
    """safe_generate_suggestions ne doit jamais lever."""
    from app.agents.pipeline import _safe_contact_suggestions

    db = _session()
    inv = Invoice(
        organization_id=1,
        filename="f.pdf",
        stored_path="/tmp/missing.pdf",
        status="ready",
        anomalies="[]",
        missing_fields="[]",
        raw_extraction=json.dumps({"supplier": "X"}),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    assert _safe_contact_suggestions(db, inv) == [] or isinstance(
        _safe_contact_suggestions(db, inv), list
    )
