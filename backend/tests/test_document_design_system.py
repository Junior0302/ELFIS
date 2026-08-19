"""Tests Document Design System — branding & PDF premium (DDS backend)."""

from __future__ import annotations

from pathlib import Path

from app.models_saas import Organization
from app.services.billing import create_sales_document
from app.services.document_branding import (
    dump_document_branding,
    parse_document_branding,
    render_config_for_document,
    resolve_show_logo,
    brand_from_organization,
)
from app.services.sales_pdf import sales_document_to_pdf


def _session():
    from app.database import SessionLocal

    return SessionLocal()


def test_resolve_show_logo_defaults():
    brand = brand_from_organization(None)
    assert resolve_show_logo(document_branding={}, brand=brand) is False
    assert resolve_show_logo(document_branding={"showLogo": True}, brand=brand) is True
    assert resolve_show_logo(document_branding={"showLogo": False}, brand=brand) is False


def test_resolve_show_logo_org_preference(tmp_path: Path, monkeypatch):
    db = _session()
    org = Organization(name="Logo Pref SA", documents_show_logo=False)
    db.add(org)
    db.commit()
    db.refresh(org)
    brand = brand_from_organization(org)
    assert resolve_show_logo(document_branding={}, brand=brand) is False
    org.documents_show_logo = True
    brand2 = brand_from_organization(org)
    assert resolve_show_logo(document_branding={}, brand=brand2) is True


def test_pdf_hides_draft_status_and_honors_show_logo():
    db = _session()
    org = Organization(
        name="Studio Alpha",
        legal_name="Studio Alpha SAS",
        siren="12345678900012",
        address="1 rue Test",
        postal_code="75001",
        city="Paris",
        phone="0102030405",
        email="a@studio.test",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    doc = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="facture",
        customer_name="Client Z",
        amount_ht=100,
        notes="Merci",
        branding={"showLogo": False},
    )
    assert doc.status == "draft"
    pdf = sales_document_to_pdf(doc, org)
    assert pdf[:4] == b"%PDF"
    # Flux compressés : on vérifie l’absence de statut technique en clair
    assert b"/draft" not in pdf.lower() and b"(draft)" not in pdf.lower()
    assert b"ComptaPilot" not in pdf
    cfg = render_config_for_document(doc, org)
    assert cfg.show_logo is False
    assert "Studio Alpha" in (cfg.brand.legal_name or cfg.brand.display_name)


def test_pdf_devis_and_avoir_metadata():
    db = _session()
    org = Organization(name="Meta Org", legal_name="Meta Org")
    db.add(org)
    db.commit()
    db.refresh(org)
    devis = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="devis",
        customer_name="Prospect",
        amount_ht=50,
        branding={"showLogo": False},
    )
    pdf_devis = sales_document_to_pdf(devis, org)
    assert pdf_devis[:4] == b"%PDF"
    assert b"ComptaPilot" not in pdf_devis
    assert b"draft" not in pdf_devis  # statut technique absent des chaînes littérales

    avoir = create_sales_document(
        db,
        organization_id=org.id,
        doc_type="avoir",
        customer_name="Client A",
        amount_ht=20,
        branding={"showLogo": False},
    )
    pdf_avoir = sales_document_to_pdf(avoir, org)
    assert pdf_avoir[:4] == b"%PDF"
    assert b"ComptaPilot" not in pdf_avoir
    assert b"draft" not in pdf_avoir

    # Métadonnées adaptées au type (fonctions pures)
    from app.services.sales_pdf import _date_meta_rows, _party_label

    assert _party_label("facture") == "Facturé à"
    assert _party_label("devis") == "Destinataire"
    assert _party_label("avoir") == "Crédit pour"
    assert any("Validité" in row[0] for row in _date_meta_rows(devis))
    assert any(row[0] == "Date" for row in _date_meta_rows(avoir))


def test_branding_json_roundtrip():
    raw = dump_document_branding(show_logo=True, template="premium_v1")
    parsed = parse_document_branding(raw)
    assert parsed["showLogo"] is True
    assert parsed["template"] == "premium_v1"
