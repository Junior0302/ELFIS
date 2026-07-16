from __future__ import annotations

import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models_saas import Organization, SalesDocument


def sales_document_to_pdf(doc: SalesDocument, organization: Organization | None = None) -> bytes:
    buffer = BytesIO()
    title_label = {"devis": "Devis", "facture": "Facture", "avoir": "Avoir"}.get(
        doc.doc_type, "Document"
    )
    pdf = SimpleDocTemplate(buffer, pagesize=A4, title=f"{title_label} {doc.number}")
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleSales",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#0B3D2E"),
        spaceAfter=10,
    )
    body = styles["Normal"]
    muted = ParagraphStyle("Muted", parent=body, textColor=colors.HexColor("#5f6b66"))

    org_name = (organization.legal_name or organization.name) if organization else "ComptaPilot"
    story = [
        Paragraph("ComptaPilot IA", muted),
        Paragraph(f"{title_label} {doc.number}", title),
        Paragraph(org_name, body),
    ]
    if organization:
        details = []
        if organization.siren:
            details.append(f"SIREN {organization.siren}")
        if organization.vat_number:
            details.append(f"TVA {organization.vat_number}")
        if organization.address:
            details.append(organization.address)
        if details:
            story.append(Paragraph(" · ".join(details), muted))
    story.append(Spacer(1, 14))

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
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7F2EC")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C3D9CD")),
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
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D2E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C3D9CD")),
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
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E7F2EC")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C3D9CD")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(totals_table)

    if doc.notes:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Notes", styles["Heading3"]))
        story.append(Paragraph(doc.notes.replace("\n", "<br/>"), body))

    pdf.build(story)
    return buffer.getvalue()
