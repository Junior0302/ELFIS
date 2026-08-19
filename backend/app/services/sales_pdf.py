from __future__ import annotations

import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models_saas import Organization, SalesDocument
from app.services.document_branding import (
    DocumentBrandProfile,
    DocumentRenderConfig,
    render_config_for_document,
)

# —— Document Design System V1 (ReportLab) ——
# Composants conceptuels : DocumentPage, Header, Brand, Title, Metadata,
# PartyBlock, ItemsTable, Totals, Notes, PaymentTerms, LegalFooter, PageNumber, Accent.


def _hex(value: str, fallback: str) -> colors.Color:
    try:
        return colors.HexColor(value)
    except Exception:
        return colors.HexColor(fallback)


def _doc_title_label(doc_type: str) -> str:
    return {"devis": "Devis", "facture": "Facture", "avoir": "Avoir"}.get(doc_type, "Document")


def _party_label(doc_type: str) -> str:
    return {
        "facture": "Facturé à",
        "devis": "Destinataire",
        "avoir": "Crédit pour",
    }.get(doc_type, "Destinataire")


def _date_meta_rows(doc: SalesDocument) -> list[list[str]]:
    """Métadonnées client — jamais de statut technique (draft, etc.)."""
    rows: list[list[str]] = [["Date", doc.issue_date or "—"]]
    if doc.doc_type == "devis":
        rows.append(["Validité", doc.due_date or "—"])
    elif doc.doc_type == "avoir":
        if doc.due_date:
            rows.append(["Référence date", doc.due_date])
    else:
        rows.append(["Échéance", doc.due_date or "—"])
    return rows


def _build_styles(primary: colors.Color) -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DdsTitle",
            parent=base["Heading1"],
            textColor=primary,
            fontSize=20,
            spaceAfter=4,
            fontName="Helvetica-Bold",
            leading=24,
        ),
        "subtitle": ParagraphStyle(
            "DdsSubtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#3d4743"),
            leading=13,
        ),
        "body": ParagraphStyle("DdsBody", parent=base["Normal"], fontSize=9, leading=12),
        "strong": ParagraphStyle(
            "DdsStrong",
            parent=base["Normal"],
            fontSize=16,
            textColor=primary,
            fontName="Helvetica-Bold",
            leading=19,
        ),
        "brand_name": ParagraphStyle(
            "DdsBrandName",
            parent=base["Normal"],
            fontSize=15,
            textColor=primary,
            fontName="Helvetica-Bold",
            leading=18,
        ),
        "section": ParagraphStyle(
            "DdsSection",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#6a756f"),
            fontName="Helvetica-Bold",
            leading=10,
            spaceAfter=3,
        ),
        "muted": ParagraphStyle(
            "DdsMuted",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#5f6b66"),
            leading=11,
        ),
        "ttc": ParagraphStyle(
            "DdsTtc",
            parent=base["Normal"],
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=primary,
            leading=15,
        ),
    }


def _accent_rule(primary: colors.Color, width: float = 175 * mm) -> Table:
    """Accent — filet discret sous l’en-tête."""
    t = Table([[""]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 1.0, primary),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _thin_rule(width: float = 175 * mm) -> Table:
    t = Table([[""]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D4CE")),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def dds_header_brand(config: DocumentRenderConfig, styles: dict) -> list:
    """Header + Brand — logo à gauche si showLogo + fichier ; sinon nom fort."""
    brand = config.brand
    primary = _hex(brand.primary_color, "#0B3D2E")
    body = styles["body"]
    brand_name = styles["brand_name"]

    address_lines = brand.address_block_lines()
    left_cell: object
    if config.render_logo and brand.logo_path is not None:
        img = Image(str(brand.logo_path))
        img._restrictSize(38 * mm, 18 * mm)
        left_cell = img
        right_name_lines = address_lines
    else:
        title_name = brand.org_name_strong or "Entreprise"
        left_cell = Paragraph(title_name, brand_name)
        right_name_lines = address_lines[1:] if address_lines else []

    right_bits: list[str] = list(right_name_lines)
    for line in brand.contact_lines():
        right_bits.append(line)
    for line in brand.legal_id_lines()[:2]:
        right_bits.append(line)

    right_html = "<br/>".join(right_bits) if right_bits else "&nbsp;"

    table = Table([[left_cell, Paragraph(right_html, body)]], colWidths=[72 * mm, 103 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [table, Spacer(1, 4), _accent_rule(primary), Spacer(1, 10)]


def dds_title_metadata(doc: SalesDocument, styles: dict) -> list:
    """Title + Metadata — type, numéro, dates (sans statut draft)."""
    title_label = _doc_title_label(doc.doc_type)
    left = [
        Paragraph(title_label, styles["title"]),
        Paragraph(f"N° {doc.number}", styles["subtitle"]),
    ]
    meta_rows = _date_meta_rows(doc)
    meta = Table(meta_rows, colWidths=[28 * mm, 40 * mm])
    meta.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6a756f")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    row = Table([[left, meta]], colWidths=[105 * mm, 70 * mm])
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [row, Spacer(1, 10), _thin_rule(), Spacer(1, 8)]


def dds_party_block(doc: SalesDocument, styles: dict) -> list:
    """PartyBlock — Facturé à / Destinataire / Crédit pour."""
    label = _party_label(doc.doc_type)
    bits = [doc.customer_name or "—"]
    if (doc.customer_email or "").strip():
        bits.append(doc.customer_email.strip())
    html = "<br/>".join(bits)
    block = [
        Paragraph(label.upper(), styles["section"]),
        Paragraph(html, styles["body"]),
    ]
    return [*block, Spacer(1, 10), _thin_rule(), Spacer(1, 8)]


def dds_items_table(doc: SalesDocument, primary: colors.Color, styles: dict) -> list:
    """ItemsTable — lignes avec séparateurs fins."""
    lines = json.loads(doc.lines_json or "[]")
    if not lines:
        return []
    header_bg = primary
    rows = [["Désignation", "Qté", "PU HT", "Total HT"]]
    for line in lines:
        qty = float(line.get("quantity") or line.get("qty") or 1)
        unit = float(line.get("unit_price") or line.get("price") or 0)
        total = float(line.get("total") or qty * unit)
        rows.append(
            [
                Paragraph(
                    str(line.get("label") or line.get("description") or "Prestation"),
                    styles["body"],
                ),
                f"{qty:g}",
                f"{unit:.2f} €",
                f"{total:.2f} €",
            ]
        )
    table = Table(rows, colWidths=[95 * mm, 20 * mm, 30 * mm, 30 * mm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
    ]
    for i in range(1, len(rows)):
        style_cmds.append(("LINEBELOW", (0, i), (-1, i), 0.35, colors.HexColor("#D5DED8")))
    table.setStyle(TableStyle(style_cmds))
    return [table, Spacer(1, 12)]


def dds_totals(doc: SalesDocument, brand: DocumentBrandProfile, styles: dict) -> list:
    """Totals — TTC dominant."""
    primary = _hex(brand.primary_color, "#0B3D2E")
    secondary = _hex(brand.secondary_color, "#E7F2EC")
    rows = [
        ["Total HT", f"{doc.amount_ht:.2f} €"],
        [f"TVA ({doc.vat_rate:g} %)", f"{doc.amount_tva:.2f} €"],
        [Paragraph("Total TTC", styles["ttc"]), Paragraph(f"{doc.amount_ttc:.2f} €", styles["ttc"])],
    ]
    table = Table(rows, colWidths=[45 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, 1), 9),
                ("TEXTCOLOR", (0, 0), (-1, 1), colors.HexColor("#3d4743")),
                ("BACKGROUND", (0, -1), (-1, -1), secondary),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, -1), (-1, -1), 0.6, primary),
            ]
        )
    )
    wrapper = Table([[Spacer(1, 1), table]], colWidths=[90 * mm, 85 * mm])
    wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [KeepTogether([wrapper]), Spacer(1, 12)]


def dds_notes_payment(doc: SalesDocument, styles: dict) -> list:
    """Notes + PaymentTerms — données réelles uniquement."""
    blocks: list = []
    if (doc.notes or "").strip():
        blocks.append(Paragraph("Notes", styles["section"]))
        blocks.append(Paragraph(doc.notes.replace("\n", "<br/>"), styles["body"]))
        blocks.append(Spacer(1, 6))
    if doc.doc_type == "facture" and (doc.due_date or "").strip():
        blocks.append(Paragraph("Conditions de paiement", styles["section"]))
        blocks.append(Paragraph(f"Échéance : {doc.due_date}", styles["body"]))
        blocks.append(Spacer(1, 6))
    elif doc.doc_type == "devis" and (doc.due_date or "").strip():
        blocks.append(Paragraph("Validité de l’offre", styles["section"]))
        blocks.append(Paragraph(f"Valable jusqu’au {doc.due_date}", styles["body"]))
        blocks.append(Spacer(1, 6))
    return blocks


def _legal_footer_canvas(brand: DocumentBrandProfile):
    """LegalFooter + PageNumber — mentions réelles only, jamais inventées."""
    primary = _hex(brand.primary_color, "#0B3D2E")
    parts = brand.footer_parts()
    footer_text = " · ".join(parts) if parts else ""

    def _draw(canvas, doc):  # noqa: ANN001
        canvas.saveState()
        canvas.setStrokeColor(primary)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#5f6b66"))
        if footer_text:
            canvas.drawString(18 * mm, 10 * mm, footer_text[:140])
            if len(footer_text) > 140:
                canvas.drawString(18 * mm, 7 * mm, footer_text[140:280])
        page = canvas.getPageNumber()
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {page}")
        canvas.restoreState()

    return _draw


def sales_document_to_pdf(doc: SalesDocument, organization: Organization | None = None) -> bytes:
    """Génère le PDF devis/facture/avoir (DDS premium V1). Ne modifie pas numéros ni montants."""
    config = render_config_for_document(doc, organization)
    brand = config.brand
    buffer = BytesIO()
    title_label = _doc_title_label(doc.doc_type)
    primary = _hex(brand.primary_color, "#0B3D2E")

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"{title_label} {doc.number}",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=22 * mm,
    )
    styles = _build_styles(primary)

    story: list = []
    story.extend(dds_header_brand(config, styles))
    story.extend(dds_title_metadata(doc, styles))
    story.extend(dds_party_block(doc, styles))
    story.extend(dds_items_table(doc, primary, styles))
    story.extend(dds_totals(doc, brand, styles))
    story.extend(dds_notes_payment(doc, styles))

    pdf.build(story, onFirstPage=_legal_footer_canvas(brand), onLaterPages=_legal_footer_canvas(brand))
    return buffer.getvalue()
