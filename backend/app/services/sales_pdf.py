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
from app.services.document_branding import DocumentBrandProfile, brand_from_organization


def _hex(value: str, fallback: str) -> colors.Color:
    try:
        return colors.HexColor(value)
    except Exception:
        return colors.HexColor(fallback)


def _header_flowables(brand: DocumentBrandProfile, styles: dict) -> list:
    primary = _hex(brand.primary_color, "#0B3D2E")
    muted = styles["muted"]
    strong = styles["strong"]
    body = styles["body"]

    address_lines = brand.address_block_lines()
    left_cell: object
    if brand.has_logo and brand.logo_path is not None:
        img = Image(str(brand.logo_path))
        img._restrictSize(42 * mm, 22 * mm)
        left_cell = img
        right_name_lines = address_lines
    else:
        title_name = brand.legal_name or brand.display_name or "Entreprise"
        left_cell = Paragraph(title_name, strong)
        # Évite de dupliquer la raison sociale déjà affichée à gauche
        right_name_lines = address_lines[1:] if address_lines else []

    right_bits: list[str] = list(right_name_lines)
    for line in brand.contact_lines():
        right_bits.append(line)
    for line in brand.legal_id_lines():
        right_bits.append(line)
    for line in brand.bank_lines():
        right_bits.append(line)

    right_html = "<br/>".join(right_bits) if right_bits else "&nbsp;"

    table = Table([[left_cell, Paragraph(right_html, body)]], colWidths=[70 * mm, 105 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, primary),
            ]
        )
    )
    return [table, Spacer(1, 10), Paragraph(" ", muted)]


def _footer_canvas(brand: DocumentBrandProfile):
    primary = _hex(brand.primary_color, "#0B3D2E")
    parts = brand.footer_parts()
    footer_text = " · ".join(parts) if parts else ""

    def _draw(canvas, doc):  # noqa: ANN001
        canvas.saveState()
        canvas.setStrokeColor(primary)
        canvas.setLineWidth(0.6)
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
    """Génère le PDF devis/facture/avoir. Ne modifie pas numéros ni montants."""
    brand = brand_from_organization(organization)
    buffer = BytesIO()
    title_label = {"devis": "Devis", "facture": "Facture", "avoir": "Avoir"}.get(
        doc.doc_type, "Document"
    )
    primary = _hex(brand.primary_color, "#0B3D2E")
    secondary = _hex(brand.secondary_color, "#E7F2EC")
    grid = colors.HexColor("#C3D9CD")

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"{title_label} {doc.number}",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=22 * mm,
    )
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleSales",
            parent=base["Heading1"],
            textColor=primary,
            fontSize=18,
            spaceAfter=8,
        ),
        "body": ParagraphStyle("BodySales", parent=base["Normal"], fontSize=9, leading=12),
        "strong": ParagraphStyle(
            "StrongSales",
            parent=base["Normal"],
            fontSize=14,
            textColor=primary,
            fontName="Helvetica-Bold",
            leading=17,
        ),
        "muted": ParagraphStyle(
            "MutedSales",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#5f6b66"),
            leading=11,
        ),
    }

    story: list = []
    story.extend(_header_flowables(brand, styles))
    story.append(Paragraph(f"{title_label} {doc.number}", styles["title"]))
    story.append(Spacer(1, 6))

    meta = [
        ["Client", doc.customer_name or "—"],
        ["Email", doc.customer_email or "—"],
        ["Date", doc.issue_date or "—"],
        ["Échéance", doc.due_date or "—"],
        ["Statut", doc.status or "—"],
    ]
    meta_table = Table(meta, colWidths=[120, 340])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), secondary),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, grid),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 16))

    lines = json.loads(doc.lines_json or "[]")
    if lines:
        rows = [["Désignation", "Qté", "PU HT", "Total HT"]]
        for line in lines:
            qty = float(line.get("quantity") or line.get("qty") or 1)
            unit = float(line.get("unit_price") or line.get("price") or 0)
            total = float(line.get("total") or qty * unit)
            rows.append(
                [
                    str(line.get("label") or line.get("description") or "Prestation"),
                    f"{qty:g}",
                    f"{unit:.2f} €",
                    f"{total:.2f} €",
                ]
            )
        line_table = Table(rows, colWidths=[240, 60, 80, 80])
        line_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, grid),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(line_table)
        story.append(Spacer(1, 14))

    totals = [
        ["Total HT", f"{doc.amount_ht:.2f} €"],
        [f"TVA ({doc.vat_rate:g} %)", f"{doc.amount_tva:.2f} €"],
        ["Total TTC", f"{doc.amount_ttc:.2f} €"],
    ]
    totals_table = Table(totals, colWidths=[120, 120])
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), secondary),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, grid),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(KeepTogether([totals_table]))

    if doc.notes:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Notes", base["Heading3"]))
        story.append(Paragraph(doc.notes.replace("\n", "<br/>"), styles["body"]))

    pdf.build(story, onFirstPage=_footer_canvas(brand), onLaterPages=_footer_canvas(brand))
    return buffer.getvalue()
