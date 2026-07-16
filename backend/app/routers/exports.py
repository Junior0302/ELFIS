from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models import Invoice
from app.services.export_excel import invoice_to_excel, invoices_to_excel
from app.services.export_pdf import invoice_to_pdf
from app.services.export_software import SOFTWARE_TARGETS, export_software

router = APIRouter(
    prefix="/exports",
    tags=["exports"],
    dependencies=[Depends(require_active_subscription)],
)


def _invoice_for_org(db: Session, invoice_id: int, organization_id: int) -> Invoice:
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )
    if not invoice:
        raise HTTPException(404, detail="Document introuvable")
    return invoice


@router.get("/formats")
def list_formats(auth: AuthContext = Depends(get_auth_context)):
    auth.require("documents.read")
    return {
        "module": "Module 1 — Comptabilité",
        "formats": [
            {"id": "fec", "label": "FEC (DGFiP)", "ext": "txt"},
            {"id": "sage", "label": "Sage", "ext": "csv"},
            {"id": "pennylane", "label": "Pennylane", "ext": "csv"},
            {"id": "cegid", "label": "Cegid", "ext": "csv"},
            {"id": "ebp", "label": "EBP", "ext": "csv"},
            {"id": "odoo", "label": "Odoo", "ext": "csv"},
            {"id": "csv", "label": "CSV générique", "ext": "csv"},
            {"id": "excel", "label": "Excel ComptaPilot", "ext": "xlsx"},
            {"id": "pdf", "label": "PDF fiche", "ext": "pdf"},
        ],
        "targets": list(SOFTWARE_TARGETS),
    }


@router.get("/history/excel")
def export_history_excel(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    invoices = (
        db.query(Invoice)
        .filter(Invoice.organization_id == auth.require_organization_id())
        .order_by(Invoice.created_at.desc())
        .all()
    )
    content = invoices_to_excel(invoices)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="comptapilot_historique.xlsx"'},
    )


@router.get("/history/{target}")
def export_history_software(
    target: str,
    status: str | None = Query(None),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    query = (
        db.query(Invoice)
        .filter(Invoice.organization_id == auth.require_organization_id())
        .order_by(Invoice.created_at.desc())
    )
    if target.lower() == "excel":
        content = invoices_to_excel(query.all())
        return Response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="comptapilot_historique.xlsx"'},
        )
    if status:
        query = query.filter(Invoice.status == status)
    invoices = query.all()
    try:
        content, media, filename = export_software(target, invoices)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return Response(
        content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="comptapilot_historique_{filename}"'},
    )


@router.get("/{invoice_id}/excel")
def export_excel(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    invoice = _invoice_for_org(db, invoice_id, auth.require_organization_id())
    content = invoice_to_excel(invoice)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="comptapilot_{invoice_id}.xlsx"'},
    )


@router.get("/{invoice_id}/pdf")
def export_pdf(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    invoice = _invoice_for_org(db, invoice_id, auth.require_organization_id())
    content = invoice_to_pdf(invoice)
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comptapilot_{invoice_id}.pdf"'},
    )


@router.get("/{invoice_id}/{target}")
def export_invoice_software(
    invoice_id: int,
    target: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    invoice = _invoice_for_org(db, invoice_id, auth.require_organization_id())
    try:
        content, media, filename = export_software(target, [invoice])
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return Response(
        content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="comptapilot_{invoice_id}_{filename}"'},
    )
