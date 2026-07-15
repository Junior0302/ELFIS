from __future__ import annotations

import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Invoice
from app.schemas import AccountingEntry


def invoice_to_pdf(invoice: Invoice) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"ComptaPilot-{invoice.id}")
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCP",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#0B3D2E"),
        spaceAfter=12,
    )
    body = styles["Normal"]

    story = [
        Paragraph("ComptaPilot IA — Fiche comptable", title),
        Paragraph(f"Document #{invoice.id} — {invoice.filename}", body),
        Spacer(1, 12),
    ]

    data = [
        ["Fournisseur", invoice.supplier or "—"],
        ["Date", invoice.invoice_date or "—"],
        ["Numéro", invoice.invoice_number or "—"],
        ["HT", f"{invoice.amount_ht:.2f} €" if invoice.amount_ht is not None else "—"],
        ["TVA", f"{invoice.amount_tva:.2f} €" if invoice.amount_tva is not None else "—"],
        ["TTC", f"{invoice.amount_ttc:.2f} €" if invoice.amount_ttc is not None else "—"],
        ["Taux TVA", f"{invoice.vat_rate} %" if invoice.vat_rate is not None else "—"],
        ["Type", invoice.document_type or "—"],
        [
            "Confiance",
            f"{invoice.confidence_score:.0%}" if invoice.confidence_score is not None else "—",
        ],
        ["Statut", invoice.status],
    ]
    table = Table(data, colWidths=[140, 320])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7F2EC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#10241C")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C3D9CD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 18))

    if invoice.accounting_entry:
        entry = AccountingEntry.model_validate_json(invoice.accounting_entry)
        story.append(Paragraph("Écriture proposée", styles["Heading2"]))
        story.append(Paragraph(entry.label, body))
        story.append(Paragraph(entry.explanation, body))
        story.append(Spacer(1, 8))
        lines = [["Compte", "Libellé", "Débit", "Crédit"]]
        for line in entry.lines:
            lines.append(
                [
                    line.account,
                    line.label,
                    f"{line.debit:.2f}",
                    f"{line.credit:.2f}",
                ]
            )
        t2 = Table(lines, colWidths=[70, 250, 70, 70])
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D2E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C3D9CD")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ]
            )
        )
        story.append(t2)

    anomalies = json.loads(invoice.anomalies or "[]")
    if anomalies:
        story.append(Spacer(1, 14))
        story.append(Paragraph("Anomalies", styles["Heading2"]))
        for a in anomalies:
            story.append(Paragraph(f"• {a}", body))

    doc.build(story)
    return buffer.getvalue()