from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.elfis_ai.chat import answer_elfis_chat
from app.elfis_ai.intelligence import build_intelligence_overview
from app.elfis_ai.orchestrator import get_latest_analysis, report_from_analysis, run_elfis_analysis
from app.models import ElfisAnalysis, Invoice

router = APIRouter(
    prefix="/elfis-ai",
    tags=["elfis-ai"],
    dependencies=[Depends(require_active_subscription)],
)


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


def _organization_invoice(db: Session, invoice_id: int, organization_id: int) -> Invoice:
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.organization_id == organization_id)
        .first()
    )
    if not invoice:
        raise HTTPException(404, detail="Document introuvable")
    return invoice


@router.get("/documents/{invoice_id}/report")
def get_report(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    org_id = auth.require_organization_id()
    invoice = _organization_invoice(db, invoice_id, org_id)
    row = get_latest_analysis(db, invoice.id, org_id)
    if not row:
        # Génération lazy si absente
        try:
            row = run_elfis_analysis(
                db,
                invoice,
                user_id=auth.user.id if auth.user else None,
            )
        except Exception as exc:
            raise HTTPException(500, detail=f"Analyse ELFIS indisponible: {exc}") from exc
    report = report_from_analysis(row)
    history_rows = (
        db.query(ElfisAnalysis)
        .filter(
            ElfisAnalysis.invoice_id == invoice.id,
            ElfisAnalysis.organization_id == org_id,
        )
        .order_by(ElfisAnalysis.id.desc())
        .limit(10)
        .all()
    )
    return {
        "report": report.model_dump(mode="json"),
        "history": [
            {
                "id": h.id,
                "created_at": h.created_at.isoformat() if h.created_at else None,
                "analysis_version": h.analysis_version,
                "processing_time_ms": h.processing_time_ms,
                "status": h.status,
            }
            for h in history_rows
        ],
    }


@router.post("/documents/{invoice_id}/reanalyze")
def reanalyze(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.write")
    org_id = auth.require_organization_id()
    invoice = _organization_invoice(db, invoice_id, org_id)
    try:
        row = run_elfis_analysis(
            db,
            invoice,
            user_id=auth.user.id if auth.user else None,
        )
    except Exception as exc:
        raise HTTPException(500, detail=f"Réanalyse impossible: {exc}") from exc
    return {"report": report_from_analysis(row).model_dump(mode="json")}


@router.get("/documents/{invoice_id}/export.json")
def export_json(
    invoice_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.read")
    org_id = auth.require_organization_id()
    invoice = _organization_invoice(db, invoice_id, org_id)
    row = get_latest_analysis(db, invoice.id, org_id)
    if not row:
        row = run_elfis_analysis(db, invoice, user_id=auth.user.id if auth.user else None)
    payload = {
        "elfis_report": report_from_analysis(row).model_dump(mode="json"),
        "invoice": {
            "id": invoice.id,
            "filename": invoice.filename,
            "supplier": invoice.supplier,
            "invoice_number": invoice.invoice_number,
            "amount_ht": invoice.amount_ht,
            "amount_tva": invoice.amount_tva,
            "amount_ttc": invoice.amount_ttc,
            "status": invoice.status,
        },
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="elfis-{invoice.id}.json"'},
    )


@router.get("/intelligence")
def intelligence(
    period: str = Query("month"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("ai.analysis")
    org_id = auth.require_organization_id()
    if period not in {"month", "previous_month", "quarter", "year"}:
        period = "month"
    return build_intelligence_overview(db, org_id, period=period)  # type: ignore[arg-type]


@router.post("/chat")
def chat(
    payload: ChatIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("ai.analysis")
    org_id = auth.require_organization_id()
    return answer_elfis_chat(db, org_id, payload.question)
