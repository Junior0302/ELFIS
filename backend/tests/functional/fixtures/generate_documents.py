"""Génère les PDF de recette synthétiques (aucune donnée réelle)."""

from __future__ import annotations

from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent / "documents"


def ensure_document_fixtures() -> dict[str, Path]:
    from tests.document_intelligence import make_empty_pdf, make_text_pdf

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}

    specs = {
        "invoice_supplier_valid.pdf": (
            "FACTURE FOURNISSEUR\n"
            "Fournisseur: Fournisseur Fictif SA\n"
            "SIRET: 90000000000000\n"
            "N facture: FAC-F-2026-001\n"
            "Date: 2026-07-01\n"
            "Echeance: 2026-07-31\n"
            "Devise: EUR\n"
            "Montant HT: 100.00\n"
            "TVA 20%: 20.00\n"
            "Montant TTC: 120.00\n"
        ),
        "invoice_customer_valid.pdf": (
            "FACTURE CLIENT\n"
            "Client: Client Fictif SARL\n"
            "N facture: FAC-C-2026-001\n"
            "Date: 2026-07-02\n"
            "HT: 200.00 TVA: 40.00 TTC: 240.00 EUR\n"
        ),
        "credit_note_supplier.pdf": (
            "AVOIR FOURNISSEUR\n"
            "Avoir N: AV-F-001\n"
            "HT: -50.00 TVA: -10.00 TTC: -60.00\n"
        ),
        "quote_valid.pdf": (
            "DEVIS\n"
            "Devis N: DEV-001\n"
            "Client: Prospect Fictif\n"
            "HT: 500.00 TVA: 100.00 TTC: 600.00\n"
        ),
        "receipt_ticket.pdf": (
            "TICKET CAISSE\n"
            "Commerce Fictif\n"
            "Total TTC: 12.50 EUR\n"
        ),
        "invoice_missing_field.pdf": (
            "FACTURE\n"
            "Fournisseur: Incomplet SA\n"
            "Montant TTC: 120.00\n"
        ),
        "invoice_unbalanced.pdf": (
            "FACTURE\n"
            "Fournisseur: Incoherent SA\n"
            "HT: 100.00\n"
            "TVA: 20.00\n"
            "TTC: 999.00\n"
        ),
        "invoice_requires_review.pdf": (
            "FACTURE COMPLEXE\n"
            "Fournisseur: Nouveau Fournisseur XYZ\n"
            "Client: Nouveau Client ABC\n"
            "HT: 10000.00 TVA: 2000.00 TTC: 12000.00\n"
            "Note: montant eleve — review humaine\n"
        ),
        "invoice_text_pdf.pdf": (
            "PDF TEXTE EXTRACTIBLE\n"
            "Facture FAC-TXT-1 HT 80 TVA 16 TTC 96\n"
        ),
        "invoice_known_supplier.pdf": (
            "FACTURE\n"
            "Fournisseur: Fournisseur Fictif SA\n"
            "FAC-KNOWN-1 HT 100 TVA 20 TTC 120\n"
        ),
        "invoice_new_supplier.pdf": (
            "FACTURE\n"
            "Fournisseur: Brand New Supplier Recette\n"
            "FAC-NEW-S HT 70 TVA 14 TTC 84\n"
        ),
        "invoice_new_customer.pdf": (
            "FACTURE CLIENT\n"
            "Client: Brand New Customer Recette\n"
            "FAC-NEW-C HT 90 TVA 18 TTC 108\n"
        ),
    }

    for name, text in specs.items():
        path = DOCS_DIR / name
        path.write_bytes(make_text_pdf(text))
        files[name] = path

    empty = DOCS_DIR / "pdf_empty.pdf"
    empty.write_bytes(make_empty_pdf())
    files["pdf_empty.pdf"] = empty

    corrupt = DOCS_DIR / "pdf_corrupt.pdf"
    corrupt.write_bytes(b"%PDF-broken-not-a-real-file")
    files["pdf_corrupt.pdf"] = corrupt

    double_ext = DOCS_DIR / "invoice.php.pdf"
    double_ext.write_bytes(make_text_pdf("Double extension test"))
    files["invoice.php.pdf"] = double_ext

    fake = DOCS_DIR / "not_a_pdf.pdf"
    fake.write_bytes(b"this is not a pdf at all")
    files["not_a_pdf.pdf"] = fake

    scanned = DOCS_DIR / "pdf_scanned_needs_ocr.pdf"
    scanned.write_bytes(make_empty_pdf())
    files["pdf_scanned_needs_ocr.pdf"] = scanned

    huge_meta = DOCS_DIR / "TOO_LARGE.marker.txt"
    huge_meta.write_text(
        "Simuler Content-Length / taille > limite dans le scénario",
        encoding="utf-8",
    )
    files["TOO_LARGE.marker.txt"] = huge_meta

    readme = DOCS_DIR / "README.md"
    readme.write_text(
        "# Documents de recette\n\n"
        "Tous synthétiques — aucune donnée personnelle réelle.\n"
        "Générés par `generate_documents.py`.\n",
        encoding="utf-8",
    )
    return files


if __name__ == "__main__":
    import sys

    backend = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(backend))
    created = ensure_document_fixtures()
    print(f"Generated {len(created)} fixtures in {DOCS_DIR}")
