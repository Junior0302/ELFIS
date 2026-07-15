from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models import Invoice
from app.schemas import DashboardStats
from app.services.finance_agent import pilot_kpis
from app.services.serializers import serialize_invoice

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("invoice.read")
    query = db.query(Invoice).filter(Invoice.organization_id == (auth.organization_id or 0))
    invoice_count = query.count()
    total_ht = query.with_entities(func.coalesce(func.sum(Invoice.amount_ht), 0.0)).scalar() or 0.0
    recoverable_vat = (
        query.with_entities(func.coalesce(func.sum(Invoice.amount_tva), 0.0)).scalar() or 0.0
    )
    to_review = query.filter(Invoice.needs_review.is_(True)).count()
    recent = query.order_by(Invoice.created_at.desc()).limit(8).all()
    return DashboardStats(
        invoice_count=invoice_count,
        total_ht=float(total_ht),
        recoverable_vat=float(recoverable_vat),
        to_review=to_review,
        recent=[serialize_invoice(i) for i in recent],
    )


@router.get("/pilot")
def dashboard_pilot(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    return pilot_kpis(db, auth.organization_id)
