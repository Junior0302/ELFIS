"""Commercial Proposal Engine — PDF generation (ReportLab).

Mirrors app/services/sales_pdf.py structure but is kept self-contained inside
sales_proposals so this bounded context has no hard dependency on ComptaPilot's
sales document PDF renderer. Generated PDFs are always marked as unsigned
drafts — a Commercial Proposal is a negotiation document, not a legal invoice.
"""

from __future__ import annotations

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

from app.models_saas import Organization
from app.services.document_branding import DocumentBrandProfile, brand_from_organization

from app.sales_proposals.models import (
    CommercialProposal,
    CommercialProposalLine,
    CommercialProposalVersion,
)

PROPOSAL_TYPE_LABELS: dict[str, str] = {
    "quote": "Devis",
    "commercial_offer": "Offre commerciale",
    "service_proposal": "Proposition de service",
    "estimate": "Devis estimatif",
    "renewal": "Proposition de renouvellement",
    "amendment": "Avenant",
    "subscription_offer": "Offre d'abonnement",
}

UNSIGNED_NOTICE = (
    "Document non signé — proposition commerciale générée automatiquement. "
    "Ne constitue pas une facture ni un contrat engageant tant qu'il n'a pas été "
    "formellement accepté par les deux parties."
)


def _hex(value: str, fallback: str) -> colors.Color:
    try:
        return colors.HexColor(value)
    except Exception:
        return colors.HexColor(fallback)


def _header_flowables(brand: DocumentBrandProfile, styles: dict) -> list:
    primary = _hex(brand.primary_color, "#0B3D2E")
    body = styles["body"]
    strong = styles["strong"]

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
        right_name_lines = address_lines[1:] if address_lines else []

    right_bits: list[str] = list(right_name_lines)
    right_bits.extend(brand.contact_lines())
    right_bits.extend(brand.legal_id_lines())
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
    return [table, Spacer(1, 10)]


def _footer_canvas(brand: DocumentBrandProfile):
    primary = _hex(brand.primary_color, "#0B3D2E")
    parts = brand.footer_parts()
    footer_text = " · ".join(parts) if parts else ""

    def _draw(canvas, doc):  # noqa: ANN001
        canvas.saveState()
        canvas.setStrokeColor(primary)
        canvas.setLineWidth(0.6)
        canvas.line(18 * mm, 20 * mm, A4[0] - 18 * mm, 20 * mm)
        canvas.setFont("Helvetica-Oblique", 6.5)
        canvas.setFillColor(colors.HexColor("#8a2f2f"))
        canvas.drawCentredString(A4[0] / 2, 15 * mm, "DOCUMENT NON SIGNÉ — VALEUR CONTRACTUELLE NULLE TANT QUE NON ACCEPTÉ")
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


def proposal_version_to_pdf(
    organization: Organization | None,
    proposal: CommercialProposal,
    version: CommercialProposalVersion,
    lines: list[CommercialProposalLine],
    company_name: str | None = None,
    contact_name: str | None = None,
) -> bytes:
    """Génère le PDF (non signé) d'une version de proposition commerciale.

    Ne modifie ni numéro ni montants — lecture seule sur les objets fournis.
    """
    brand = brand_from_organization(organization)
    buffer = BytesIO()
    title_label = PROPOSAL_TYPE_LABELS.get(proposal.proposal_type, "Proposition commerciale")
    primary = _hex(brand.primary_color, "#0B3D2E")
    secondary = _hex(brand.secondary_color, "#E7F2EC")
    grid = colors.HexColor("#C3D9CD")

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"{title_label} {proposal.proposal_number} v{version.version_number}",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=26 * mm,
    )
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleProposal",
            parent=base["Heading1"],
            textColor=primary,
            fontSize=18,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleProposal",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#5f6b66"),
            spaceAfter=8,
        ),
        "body": ParagraphStyle("BodyProposal", parent=base["Normal"], fontSize=9, leading=12),
        "strong": ParagraphStyle(
            "StrongProposal",
            parent=base["Normal"],
            fontSize=14,
            textColor=primary,
            fontName="Helvetica-Bold",
            leading=17,
        ),
        "section": ParagraphStyle(
            "SectionProposal",
            parent=base["Heading3"],
            textColor=primary,
            fontSize=11,
            spaceBefore=10,
            spaceAfter=4,
        ),
    }

    story: list = []
    story.extend(_header_flowables(brand, styles))
    story.append(Paragraph(f"{title_label} {proposal.proposal_number}", styles["title"]))
    story.append(Paragraph(f"Version {version.version_number} — statut : {version.status}", styles["subtitle"]))
    story.append(Spacer(1, 6))

    seller_name = brand.legal_name or brand.display_name or "Notre entreprise"
    buyer_name = (company_name or "—").strip() or "—"
    buyer_contact = (contact_name or "—").strip() or "—"

    meta = [
        ["Émetteur", seller_name],
        ["Client", buyer_name],
        ["Contact", buyer_contact],
        ["Validité", version.valid_until.isoformat() if version.valid_until else "—"],
        ["Devise", version.currency or proposal.currency or "EUR"],
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
    story.append(Spacer(1, 14))

    if version.introduction:
        story.append(Paragraph("Introduction", styles["section"]))
        story.append(Paragraph(version.introduction.replace("\n", "<br/>"), styles["body"]))

    if version.scope:
        story.append(Paragraph("Périmètre", styles["section"]))
        story.append(Paragraph(version.scope.replace("\n", "<br/>"), styles["body"]))

    if lines:
        story.append(Paragraph("Détail de la proposition", styles["section"]))
        rows = [["Désignation", "Qté", "PU HT", "Remise", "TVA", "Total TTC"]]
        for line in lines:
            qty = float(line.quantity or 0)
            unit = float(line.unit_price or 0)
            discount = float(line.discount_amount or 0)
            tax_rate = float(line.tax_rate or 0)
            total = float(line.total or 0)
            label = line.name or "Prestation"
            if line.description:
                label = f"{label}<br/><font size=7 color='#5f6b66'>{line.description}</font>"
            rows.append(
                [
                    Paragraph(label, styles["body"]),
                    f"{qty:g}",
                    f"{unit:.2f} €",
                    f"{discount:.2f} €" if discount else "—",
                    f"{tax_rate:g} %",
                    f"{total:.2f} €",
                ]
            )
        line_table = Table(rows, colWidths=[190, 40, 65, 60, 45, 70])
        line_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, grid),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(line_table)
        story.append(Spacer(1, 14))

    currency_symbol = "€" if (version.currency or "EUR").upper() == "EUR" else (version.currency or "")
    totals = [
        ["Sous-total HT", f"{float(version.subtotal or 0):.2f} {currency_symbol}"],
        ["Remises", f"-{float(version.discount_total or 0):.2f} {currency_symbol}"],
        ["TVA", f"{float(version.tax_total or 0):.2f} {currency_symbol}"],
        ["Total TTC", f"{float(version.total or 0):.2f} {currency_symbol}"],
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

    if version.payment_terms:
        story.append(Spacer(1, 14))
        story.append(Paragraph("Conditions de paiement", styles["section"]))
        story.append(Paragraph(version.payment_terms.replace("\n", "<br/>"), styles["body"]))

    if version.terms:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Conditions commerciales", styles["section"]))
        story.append(Paragraph(version.terms.replace("\n", "<br/>"), styles["body"]))

    if version.notes:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Notes", styles["section"]))
        story.append(Paragraph(version.notes.replace("\n", "<br/>"), styles["body"]))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f"<i>{UNSIGNED_NOTICE}</i>",
            ParagraphStyle(
                "UnsignedNotice",
                parent=base["Normal"],
                fontSize=7.5,
                textColor=colors.HexColor("#8a2f2f"),
            ),
        )
    )

    pdf.build(story, onFirstPage=_footer_canvas(brand), onLaterPages=_footer_canvas(brand))
    return buffer.getvalue()
