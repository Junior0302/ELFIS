from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_saas import Organization
from app.services.contacts.creation_service import create_manual_contact
from app.services.contacts.errors import InvalidContactDataError


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_create_manual_supplier():
    db = _session()
    db.add(Organization(id=1, name="Org"))
    db.commit()
    contact = create_manual_contact(
        db,
        organization_id=1,
        user_id=None,
        contact_type="supplier",
        confirmed_data={"company_name": "Fournisseur SA", "email": "f@example.com"},
    )
    assert contact.id
    assert contact.contact_type == "supplier"
    assert contact.source == "manual"
    assert contact.company_name == "Fournisseur SA"


def test_create_manual_requires_identity():
    db = _session()
    db.add(Organization(id=1, name="Org"))
    db.commit()
    try:
        create_manual_contact(
            db,
            organization_id=1,
            user_id=None,
            contact_type="supplier",
            confirmed_data={"email": "x@y.com"},
        )
        assert False, "expected InvalidContactDataError"
    except InvalidContactDataError:
        pass
