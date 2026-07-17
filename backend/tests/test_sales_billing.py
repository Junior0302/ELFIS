from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models_saas import DocumentEmailLog, Organization, SalesDocument
from app.services.billing import create_sales_document, delete_sales_document, update_sales_document
from app.services.sales_pdf import sales_document_to_pdf


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_sales_document_update_keeps_number():
    db = _session()
    org = Organization(name="Demo SA", legal_name="Demo SA")
    db.add(org)
    db.commit()
    db.refresh(org)

    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Client A",
        customer_email="a@example.com",
        amount_ht=100,
        vat_rate=20,
    )
    number = doc.number
    updated = update_sales_document(
        db,
        doc,
        customer_name="Client B",
        customer_email="b@example.com",
        amount_ht=200,
    )
    assert updated.number == number
    assert updated.customer_name == "Client B"
    assert updated.customer_email == "b@example.com"
    assert updated.amount_ttc == 240.0


def test_sales_document_delete_removes_email_logs():
    db = _session()
    org = Organization(name="Demo SA")
    db.add(org)
    db.commit()
    db.refresh(org)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="devis",
        customer_name="Client C",
        amount_ht=50,
    )
    db.add(
        DocumentEmailLog(
            sales_document_id=doc.id,
            organization_id=org.id,
            recipient="c@example.com",
            subject="Devis n°x",
            status="pending",
        )
    )
    db.commit()
    delete_sales_document(db, doc)
    assert db.get(SalesDocument, doc.id) is None
    assert db.query(DocumentEmailLog).count() == 0


def test_sales_pdf_bytes():
    db = _session()
    org = Organization(
        name="Atelier Nord",
        legal_name="Atelier Nord SAS",
        siren="12345678900012",
        vat_number="FR12345678901",
        address="1 rue Test",
        postal_code="75001",
        city="Paris",
        phone="01 23 45 67 89",
        email="contact@atelier-nord.test",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="devis",
        customer_name="Client D",
        customer_email="d@example.com",
        amount_ht=80,
        notes="Merci",
    )
    pdf = sales_document_to_pdf(doc, org)
    assert pdf[:4] == b"%PDF"
    # Identité entreprise, jamais la marque produit
    assert b"ComptaPilot" not in pdf
    from app.services.document_branding import brand_from_organization

    brand = brand_from_organization(org)
    assert "Atelier Nord" in (brand.legal_name or brand.display_name)
    assert any("SIRET" in line or "SIREN" in line for line in brand.legal_id_lines())
    assert brand.footer_parts()
